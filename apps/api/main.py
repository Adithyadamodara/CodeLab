from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kubernetes import client, config
import requests
import httpx
import time
import subprocess
import socket
import atexit
import os
import asyncio
from contextlib import asynccontextmanager

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge, Counter

# --- Metrics ---
ACTIVE_SESSIONS = Gauge("active_lab_sessions", "Number of currently active lab pods")
TOTAL_EXECUTIONS = Counter("total_executions", "Total number of code executions")
POD_CPU_USAGE = Gauge("pod_cpu_usage_cores", "CPU usage of the pod in cores", ["user_id"])
POD_MEMORY_USAGE = Gauge("pod_memory_usage_bytes", "Memory usage of the pod in bytes", ["user_id"])

# --- Global State ---
PROXY_PROCESS = None
LAST_SEEN = {} # Track last time user checked status

def cleanup_proxy():
    global PROXY_PROCESS
    if PROXY_PROCESS:
        PROXY_PROCESS.terminate()

atexit.register(cleanup_proxy)

def delete_pod(user_id: str):
    pod_name = f"python-lab-{user_id}"
    svc_name = f"python-lab-svc-{user_id}"
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace="default", body=client.V1DeleteOptions(grace_period_seconds=0))
    except Exception:
        pass
    try:
        v1.delete_namespaced_service(name=svc_name, namespace="default")
    except Exception:
        pass
    # We do NOT delete the PVC here, so workspace persists!
        
    if user_id in LAST_SEEN:
        del LAST_SEEN[user_id]


async def reaper_task():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        to_remove = []
        for user_id, last_seen in LAST_SEEN.items():
            if now - last_seen > 300: # 5 minutes
                to_remove.append(user_id)
        
        for user_id in to_remove:
            print(f"🧹 Reaping inactive pod for {user_id}")
            delete_pod(user_id)

async def metrics_task():
    custom_api = client.CustomObjectsApi()
    while True:
        await asyncio.sleep(15)
        try:
            ACTIVE_SESSIONS.set(len(LAST_SEEN))
            
            try:
                metrics = custom_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")
            except Exception as e:
                continue
                
            for item in metrics.get("items", []):
                pod_name = item["metadata"]["name"]
                if pod_name.startswith("python-lab-"):
                    user_id = pod_name.replace("python-lab-", "")
                    
                    try:
                        cpu_str = item["containers"][0]["usage"]["cpu"]
                        if cpu_str.endswith('n'):
                            cpu_cores = float(cpu_str[:-1]) / 1e9
                        elif cpu_str.endswith('m'):
                            cpu_cores = float(cpu_str[:-1]) / 1e3
                        else:
                            cpu_cores = float(cpu_str)
                        
                        POD_CPU_USAGE.labels(user_id=user_id).set(cpu_cores)
                        
                        mem_str = item["containers"][0]["usage"]["memory"]
                        if mem_str.endswith('Ki'):
                            mem_bytes = float(mem_str[:-2]) * 1024
                        elif mem_str.endswith('Mi'):
                            mem_bytes = float(mem_str[:-2]) * 1024 * 1024
                        else:
                            mem_bytes = float(mem_str)
                            
                        POD_MEMORY_USAGE.labels(user_id=user_id).set(mem_bytes)
                    except Exception as e:
                        pass
        except Exception as e:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    global PROXY_PROCESS
    # Start kubectl proxy for routing
    if "KUBERNETES_SERVICE_HOST" not in os.environ:
        PROXY_PROCESS = subprocess.Popen(
            ["kubectl", "proxy", "--port", "8001"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    # Apply default NetworkPolicy
    try:
        net_v1 = client.NetworkingV1Api()
        policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(name="deny-egress-except-dns"),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(match_labels={"app": "code-lab"}),
                policy_types=["Egress"],
                egress=[
                    client.V1NetworkPolicyEgressRule(
                        ports=[
                            client.V1NetworkPolicyPort(port=53, protocol="UDP"),
                            client.V1NetworkPolicyPort(port=53, protocol="TCP")
                        ]
                    )
                ]
            )
        )
        net_v1.create_namespaced_network_policy(namespace="default", body=policy)
    except Exception:
        pass # Might already exist

    task = asyncio.create_task(reaper_task())
    m_task = asyncio.create_task(metrics_task())
    yield
    task.cancel()
    m_task.cancel()
    if PROXY_PROCESS:
        PROXY_PROCESS.terminate()

app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

try:
    config.load_kube_config()
except Exception:
    config.load_incluster_config()

v1 = client.CoreV1Api()

class CodePayload(BaseModel):
    code: str

def create_pod_logic(user_id: str):
    pod_name = f"python-lab-{user_id}"
    svc_name = f"python-lab-svc-{user_id}"
    pvc_name = f"workspace-pvc-{user_id}"

    # Provision PVC
    pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1VolumeResourceRequirements(requests={"storage": "100Mi"})
        )
    )
    try:
        v1.create_namespaced_persistent_volume_claim(namespace="default", body=pvc)
    except Exception:
        pass # Already exists
    
    workspace_volume = client.V1Volume(
        name="workspace",
        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name)
    )
    volume_mount = client.V1VolumeMount(
        name="workspace",
        mount_path="/tmp"
    )
    security_context = client.V1SecurityContext(
        read_only_root_filesystem=True,
        allow_privilege_escalation=False,
        run_as_non_root=True,
        capabilities=client.V1Capabilities(drop=["ALL"])
    )
    container = client.V1Container(
        name="executor",
        image="my-python-executor",       
        image_pull_policy="IfNotPresent", 
        ports=[client.V1ContainerPort(container_port=5000)],
        volume_mounts=[volume_mount],
        security_context=security_context,
        resources=client.V1ResourceRequirements(
            requests={"memory": "64Mi", "cpu": "100m"},
            limits={"memory": "128Mi", "cpu": "250m"}
        )
    )
    spec = client.V1PodSpec(
        containers=[container], 
        volumes=[workspace_volume],
        restart_policy="Never",
        active_deadline_seconds=600, # 10 Minutes hard limit
        automount_service_account_token=False
    )
    metadata = client.V1ObjectMeta(name=pod_name, labels={"app": "code-lab", "user": user_id})
    pod = client.V1Pod(api_version="v1", kind="Pod", metadata=metadata, spec=spec)
    
    v1.create_namespaced_pod(namespace="default", body=pod)

    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=svc_name),
        spec=client.V1ServiceSpec(
            selector={"app": "code-lab", "user": user_id},
            ports=[client.V1ServicePort(port=5000, target_port=5000)]
        )
    )
    try:
        v1.create_namespaced_service(namespace="default", body=service)
    except Exception:
        pass

@app.post("/launch/{user_id}")
async def launch_lab(user_id: str, background_tasks: BackgroundTasks):
    try:
        LAST_SEEN[user_id] = time.time()
        pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
        if pods.items:
            pod = pods.items[0]
            return {"status": "exists", "pod_name": pod.metadata.name}
        
        background_tasks.add_task(create_pod_logic, user_id)
        return {"status": "provisioning", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{user_id}")
async def get_status(user_id: str):
    try:
        LAST_SEEN[user_id] = time.time() # Heartbeat
        pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
        if not pods.items:
            return {"phase": "NotFound"}
        
        pod = pods.items[0]
        # Calculate remaining time (max 10 minutes)
        creation_time = pod.metadata.creation_timestamp
        elapsed = time.time() - creation_time.timestamp() if creation_time else 0
        remaining = max(0, 600 - int(elapsed))
        
        if pod.status.phase == "Failed" and pod.status.reason == "DeadlineExceeded":
            return {"phase": "Expired"}
            
        if pod.status.phase == "Running":
            if "KUBERNETES_SERVICE_HOST" not in os.environ and not PROXY_PROCESS:
                return {"phase": "ProvisioningTunnel", "ip": pod.status.pod_ip, "remaining_seconds": remaining}
                
        return {
            "phase": pod.status.phase,
            "ip": pod.status.pod_ip,
            "remaining_seconds": remaining
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/pod/{user_id}")
async def terminate_lab(user_id: str):
    delete_pod(user_id)
    return {"status": "terminated"}

@app.post("/execute/{user_id}")
async def execute_code(user_id: str, payload: CodePayload):
    TOTAL_EXECUTIONS.inc()
    try:
        LAST_SEEN[user_id] = time.time()
        if "KUBERNETES_SERVICE_HOST" in os.environ:
            pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
            if not pods.items or pods.items[0].status.phase != "Running":
                raise Exception("Pod not ready")
            url = f"http://{pods.items[0].status.pod_ip}:5000/run"
        else:
            url = f"http://127.0.0.1:8001/api/v1/namespaces/default/services/python-lab-svc-{user_id}:5000/proxy/run"
            
        response = requests.post(url, json={"code": payload.code}, timeout=10)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Execution error: {str(e)}")

@app.websocket("/execute/{user_id}")
async def we_execute(websocket: WebSocket, user_id: str):
    await websocket.accept()
    TOTAL_EXECUTIONS.inc()
    LAST_SEEN[user_id] = time.time()
    try:
        data = await websocket.receive_json()
        code = data.get("code", "")

        if "KUBERNETES_SERVICE_HOST" in os.environ:
            pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
            if not pods.items or pods.items[0].status.phase != "Running":
                await websocket.send_json({"type": "error", "data": "Pod not ready"})
                await websocket.close()
                return
            pod_url = f"http://{pods.items[0].status.pod_ip}:5000/run"
        else:
            pod_url = f"http://127.0.0.1:8001/api/v1/namespaces/default/services/python-lab-svc-{user_id}:5000/proxy/run"

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", pod_url, json={"code": code}, timeout=None) as response:
                async for line in response.aiter_lines():
                    await websocket.send_json({"type": "output", "data": line})

        await websocket.send_json({"type": "system", "data": "\n Execution complete."})
        await websocket.close()

    except WebSocketDisconnect:
        print(f" User {user_id} Disconnected from WebSocket.")
    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"Internal Server Error: {str(e)}"})
        await websocket.close()