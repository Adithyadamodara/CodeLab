from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from kubernetes import client, config
import requests
import httpx  # async client for streaming
import time

app = FastAPI()

try:
    config.load_kube_config()
except Exception:
    config.load_incluster_config()

v1 = client.CoreV1Api()

class CodePayload(BaseModel):
    code: str

def create_pod_logic(user_id: str):
    pod_name = f"python-lab-{user_id}"
    
    # 1. Create an Ephemeral Volume (Workspace)
    # Since the filesystem is read-only, creating a small writable folder.
    workspace_volume = client.V1Volume(
        name="workspace",
        empty_dir=client.V1EmptyDirVolumeSource(size_limit="20Mi")
    )
    
    volume_mount = client.V1VolumeMount(
        name="workspace",
        mount_path="/tmp" # We will mount this to /tmp so the code can be written here
    )

    # 2. The Straitjacket (Security Context)
    security_context = client.V1SecurityContext(
        read_only_root_filesystem=True,   # Prevents malicious `rm -rf /` or downloading malware
        allow_privilege_escalation=False, # Blocks sudo attempts
        run_as_non_root=True,             # Forces it to use the 'sandbox' user made in Docker
        capabilities=client.V1Capabilities(drop=["ALL"]) # Strips all Linux root capabilities
    )
    
    # 3. Container Definition
    container = client.V1Container(
        name="executor",
        image="my-python-executor",       
        image_pull_policy="IfNotPresent", 
        ports=[client.V1ContainerPort(container_port=5000)],
        volume_mounts=[volume_mount],
        security_context=security_context,
        resources=client.V1ResourceRequirements(
            requests={"memory": "64Mi", "cpu": "100m"},
            limits={"memory": "128Mi", "cpu": "250m"} # Strict limits for t3.micro
        )
    )
    
    # 4. Pod Definition
    spec = client.V1PodSpec(
        containers=[container], 
        volumes=[workspace_volume],
        restart_policy="Never",
        active_deadline_seconds=900,         # THE HARD KILL: K8s violently kills the pod after 15 mins (900s)
        automount_service_account_token=False # Prevents the pod from talking to the Kubernetes API itself
    )
    
    metadata = client.V1ObjectMeta(name=pod_name, labels={"app": "code-lab", "user": user_id})
    pod = client.V1Pod(api_version="v1", kind="Pod", metadata=metadata, spec=spec)
    
    v1.create_namespaced_pod(namespace="default", body=pod)

@app.post("/launch/{user_id}")
async def launch_lab(user_id: str, background_tasks: BackgroundTasks):
    try:
        pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
        if pods.items:
            return {"status": "exists", "pod_name": pods.items[0].metadata.name}
        
        background_tasks.add_task(create_pod_logic, user_id)
        return {"status": "provisioning", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{user_id}")
async def get_status(user_id: str):
    try:
        pods = v1.list_namespaced_pod(namespace="default", label_selector=f"user={user_id}")
        if not pods.items:
            return {"phase": "NotFound"}
        
        pod = pods.items[0]
        return {
            "phase": pod.status.phase,
            "ip": pod.status.pod_ip
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/{user_id}")
async def execute_code(user_id: str, payload: CodePayload):
    # In a real AWS environment, its route directly to pod_ip
    # For local Kind testing, hitting the port-forwarded localhost
    try:
        url = "http://127.0.0.1:5000/run"
        response = requests.post(url, json={"code": payload.code}, timeout=10)
        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Pod is not ready or port-forwarding is not active.")

@app.websocket("/ws/execute/{user_id}")
async def we_execute(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            # Recieving payload from IDE
            data = await websocket.receive_json()
            code = data.get("code", "")

            # Local kind tunnel routing, pod_id for AWS
            pod_url = "http://127.0.0.1:5000/run"

            # Opening a streaming connection to the pod
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", pod_url, json={"code": code}, timeout=None) as response:
                    async for line in response.aiter_lines():
                        # Pushing every line instantly to the browser terminal
                        await websocket.send_json({"output": line})

            # Execution completion
            await websocket.send_json({"output": "\n Execution complete."})

    except WebSocketDisconnect:
        print(f" User {user_id} Disconnected from WebSocket.")
    except Exception as e:
        await websocket.send_json({"output": f"Internal Server Error: {str(e)}"})