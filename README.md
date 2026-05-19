# CodeLab 🧪

A multi-user, sandboxed cloud code execution platform. Write Python code in a browser-based editor and run it inside an isolated Kubernetes pod — with real-time streaming output, persistent workspaces, and per-user session management.

---

## Architecture

```
Browser (React + Monaco Editor)
        │
        │  HTTP / WebSocket
        ▼
FastAPI Orchestrator  ──────────────────────  :8000
        │
        │  Kubernetes API
        ▼
Kind Cluster (local)
  ├── python-lab-{user}      Pod   :5000  (executor)
  ├── python-lab-svc-{user}  Service      (ClusterIP)
  └── workspace-pvc-{user}   PVC          (100Mi, persistent)

Observability (Docker Compose)
  ├── Prometheus  :9090  ← scrapes FastAPI /metrics
  └── Grafana     :3000  ← reads Prometheus
```

---

## Project Structure

```
CodeLab/
├── apps/
│   ├── api/
│   │   └── main.py              # FastAPI orchestrator (backend core)
│   ├── executor/
│   │   └── python/
│   │       ├── executor.py      # Persistent REPL HTTP server (runs in pod)
│   │       └── Dockerfile       # Container image for the executor
│   └── codeLab/                 # React frontend (Vite + Monaco Editor)
│       └── src/
├── pipeline.py                  # Local dev launcher script
├── docker-compose.yml           # Prometheus + Grafana stack
├── prometheus.yml               # Prometheus scrape config
├── dashboard.json               # Grafana dashboard (import manually)
├── metrics-server-patched.yaml  # Kubernetes Metrics Server for Kind
└── BuildFlow.md                 # Quick-start cluster setup commands
```

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Kind](https://kind.sigs.k8s.io/) | Local Kubernetes cluster |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | Cluster management |
| [Docker](https://www.docker.com/) | Build executor image + run observability stack |
| Python 3.10+ | Run the FastAPI backend |
| Node.js 18+ | Run the React frontend |

---

## Setup & Running

### 1. Create the Kind Cluster

```bash
winget install Kubernetes.Kind

# v1.30.0 used for kubelet compatibility
kind create cluster --name code-lab-cluster --image kindest/node:v1.30.0

# Verify
kubectl cluster-info --context kind-code-lab-cluster
```

### 2. Build & Load the Executor Image

```bash
docker build -t my-python-executor ./apps/executor/python

# Load into Kind (bypasses Docker Hub pull)
kind load docker-image my-python-executor --name code-lab-cluster
```

### 3. Deploy the Metrics Server

Required for per-pod CPU/memory metrics in Grafana.

```bash
kubectl apply -f metrics-server-patched.yaml
```

> The patched version includes `--kubelet-insecure-tls` which is necessary for Kind's self-signed node certificates.

### 4. Install Backend Dependencies

```bash
cd "d:/Cloud Projects/CodeLab"
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn kubernetes httpx requests prometheus-fastapi-instrumentator prometheus-client
```

### 5. Start the Backend

**Option A — via the pipeline launcher:**
```bash
python pipeline.py
```

**Option B — directly:**
```bash
uvicorn apps.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### 6. Start the Frontend

```bash
cd apps/codeLab
npm install
npm run dev
```

### 7. Start the Observability Stack

```bash
docker-compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

Import `dashboard.json` in Grafana → Dashboards → Import to get the pre-built CodeLab dashboard.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/launch/{user_id}` | Provision a pod for the user |
| `GET` | `/status/{user_id}` | Poll pod status + heartbeat |
| `DELETE` | `/pod/{user_id}` | Terminate pod and service |
| `POST` | `/execute/{user_id}` | Run code (sync, returns full output) |
| `WS` | `/execute/{user_id}` | Run code (streaming, line-by-line output) |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## How Code Execution Works

1. The browser opens a WebSocket to `ws://localhost:8000/execute/{user_id}` and sends `{"code": "..."}`.
2. The FastAPI server routes the request to the user's pod via `kubectl proxy` (local) or direct pod IP (in-cluster).
3. Inside the pod, `executor.py` writes the code to `/tmp/script.py` and feeds it to a persistent `python3 -i` REPL subprocess via `exec()`.
4. Output is streamed back line-by-line as HTTP chunked transfer encoding.
5. FastAPI forwards each line to the browser WebSocket as `{"type": "output", "data": "..."}`.
6. A sentinel delimiter (`___END_OF_EXECUTION___`) signals end of run.

**REPL persistence:** Variables, imports, and function definitions survive across multiple runs within the same session.

---

## Session Lifecycle

```
Launch  →  Provisioning  →  Running  →  Idle (>5 min)  →  Reaped
                                              ↑
                                    Heartbeat via GET /status
```

- Pods have a **hard 10-minute limit** (`active_deadline_seconds: 600`).
- The reaper background task checks every 60 seconds and deletes pods inactive for more than 5 minutes.
- **PVCs are never deleted** — the user's `/tmp` workspace persists for future sessions.

---

## Security

| Layer | Mechanism |
|---|---|
| Network | `NetworkPolicy` blocks all pod egress except DNS (port 53) |
| Filesystem | `readOnlyRootFilesystem=true`; writes only to PVC at `/tmp` |
| Privilege | `runAsNonRoot`, `allowPrivilegeEscalation=false`, all Linux capabilities dropped |
| Kubernetes API | `automountServiceAccountToken=false` — pod cannot reach the cluster API |
| Time limit | Kubernetes hard-kills pod after 10 minutes |
| Resources | 128Mi RAM / 250m CPU hard limits per pod |

---

## Observability Metrics

| Metric | Type | Description |
|---|---|---|
| `active_lab_sessions` | Gauge | Number of users with active pods |
| `total_executions` | Counter | Cumulative code execution count |
| `pod_cpu_usage_cores` | Gauge | Per-user CPU (labelled by `user_id`) |
| `pod_memory_usage_bytes` | Gauge | Per-user memory (labelled by `user_id`) |

Raw metrics: `http://localhost:8000/metrics`

---

## License

MIT
