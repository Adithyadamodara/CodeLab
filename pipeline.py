import subprocess
import time
import requests
import atexit
import sys

# Define our processes so we can kill them on exit
api_process = None
port_forward_process = None

def cleanup():
    print("\n🧹 Cleaning up processes...")
    if port_forward_process:
        port_forward_process.terminate()
    if api_process:
        api_process.terminate()
    print("✅ Pipeline closed.")

# Register cleanup to run even if the script crashes
atexit.register(cleanup)

def run_pipeline():
    global api_process, port_forward_process
    user_id = "adithya-test"

    print("🚀 [1/5] Starting FastAPI Orchestrator...")
    # Use shell=True for Windows compatibility if needed, but list format is safer
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        stdout=subprocess.DEVNULL, # Hide uvicorn stdout
        stderr=None # Show errors if uvicorn fails to start
    )
    
    # Wait for API to boot up by pinging it instead of a fixed sleep
    print("⏳ Waiting for API to boot up...")
    api_ready = False
    for i in range(10):
        try:
            requests.get("http://127.0.0.1:8000/docs", timeout=1) # Ping docs endpoint
            api_ready = True
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            
    if not api_ready:
        print("❌ Failed to connect to API. Uvicorn might have crashed or takes too long to start.")
        sys.exit(1)

    print(f"📦 [2/5] Launching Lab Pod for user: {user_id}...")
    try:
        requests.post(f"http://127.0.0.1:8000/launch/{user_id}")
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to API. Is uvicorn running?")
        sys.exit(1)

    print("⏳ [3/5] Waiting for Kubernetes Pod to be 'Running' (this takes a few seconds)...")
    while True:
        res = requests.get(f"http://127.0.0.1:8000/status/{user_id}").json()
        phase = res.get("phase")
        if phase == "Running":
            print(f"   ↳ Pod is Running at IP: {res.get('ip')}")
            break
        elif phase == "NotFound":
            print("   ↳ Pod not found yet, retrying...")
        else:
            print(f"   ↳ Pod is currently in phase: {phase}...")
        time.sleep(2)

    print("🔌 [4/5] Establishing Network Tunnel (Port-Forwarding)...")
    pod_name = f"python-lab-{user_id}"
    port_forward_process = subprocess.Popen(
        ["kubectl", "port-forward", f"pod/{pod_name}", "5000:5000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3) # Give the tunnel time to open

    print("💻 [5/5] Executing Test Code...")
    test_code = {
        "code": "def solve(arr):\n    return sum(arr)\n\nprint(f'Sum is: {solve([1, 2, 3, 4, 5])}')"
    }
    
    try:
        result = requests.post(f"http://127.0.0.1:8000/execute/{user_id}", json=test_code, timeout=5).json()
        print("\n" + "="*40)
        print("🎯 EXECUTION RESULT:")
        print(f"Stdout: {result.get('stdout', '').strip()}")
        if result.get('stderr'):
            print(f"Stderr: {result.get('stderr', '').strip()}")
        print(f"Exit Code: {result.get('exit_code')}")
        print("="*40)
    except Exception as e:
        print(f"❌ Execution failed: {e}")

if __name__ == "__main__":
    run_pipeline()