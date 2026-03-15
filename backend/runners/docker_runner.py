import docker 
import tempfile
import os

client = docker.from_env()

# 3 second to timeout
EXECUTION_TIMEOUT = 3

def run_python_code(code: str):

    with tempfile.TemporaryDirectory() as temp_dir:
        
        file_path = os.path.join(temp_dir, "script.py")
        
        with open(file_path, "w") as f:
            f.write(code)

        try:
            container = client.containers.run(
                image="python:3.11-slim",
                command="python script.py",
                volumes={
                    temp_dir: {
                        "bind": "/app",
                        "mode": "ro"
                    }
                },
                working_dir="/app",
                mem_limit="128m", # 128mb ram
                nano_cpus=500000000, # 0.5 cpus
                network_disabled=True,
                read_only=True,
                detach=True,
                stderr=True,
                #stdout=True
            )

            container.wait(timeout = EXECUTION_TIMEOUT)
            logs = container.logs()
            return logs.decode()

        except Exception:
            
            if container:
                try:
                    container.kill()
                except:
                    pass
            
            return "Execution timed out"
        
        finally:
            
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass