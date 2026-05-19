import subprocess
import time
import requests
import atexit
import sys

api_process = None

def cleanup():
    print("\n🧹 Cleaning up processes...")
    if api_process:
        api_process.terminate()
    print("✅ Pipeline closed.")

atexit.register(cleanup)

def run_pipeline():
    global api_process

    print("🚀 [1/2] Starting FastAPI Orchestrator...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=None
    )
    
    print("⏳ Waiting for API to boot up...")
    api_ready = False
    for i in range(10):
        try:
            requests.get("http://127.0.0.1:8000/docs", timeout=1)
            api_ready = True
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            
    if not api_ready:
        print("❌ Failed to connect to API. Uvicorn might have crashed or takes too long to start.")
        sys.exit(1)

    print("💻 [2/2] Pipeline Ready!")
    print("================================================================")
    print("✅ Multi-user FastAPI Orchestrator is running on http://127.0.0.1:8000.")
    print("Pod provisioning and routing is now handled dynamically per-user.")
    print("Press CTRL+C to exit")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run_pipeline()