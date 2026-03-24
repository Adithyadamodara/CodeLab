
PHASE 1

API skeletion 

1. Started by creating backend folder.
    a. Installed uvicorn pydantic fastapi
    b. Inside backend folder - created 3 files (main.py, models.py, executor.py)
    c. models.py - defines the request schema 
    d. executor.py - initally only simulates execution ( creates job { json/dictionary with language, job_id, code, queue status })
    e. main.py - API Entry point (has a create_job function, it only creates a job from models.py and generates a job id)
    f. Backend API never executes heavy work directly
    g. They : recieve request --> create job --> delegate execution 

PHASE 2

RUNNING SANDBOX ENVIRONMENT
Redix queueing to be implemented in a later phase

Basic Controlflow

Frontend --> FastAPI Backend --> Docker Runner --> Isolated Container --> Capture stdout / stderr

Details:


Steps:

1. Install and check docker SDK
2. Created runners subfolder in backend for docker runner file
3. Docker runner file creates an isolated workspace (new temp dir) with a file script.py (for python currently) and
docker runs - docker run python:3.11-slim python script.py with a volume mount. app/script.py.
4. This container is automatically removed.
5. Updated executor.py to call run_python_code from docker_runners.py. 
6. Added main.py to to call execute function from executor.py 

Testing:
1. Tested multiple codes, output is visible, observed docker image creation and deletion.
2. Issues: infinite loops dont get found, the code executes forever, and image doesnt shutdown, also observed that the fastapi server on uvicorn wont shutdown unless all connections are stopped - here the docker container - as long as container runs the server will need to be forced to shutdown. Regular termination of server will keep it running as long as connection is active on the frontend, as soon as connection stops the server will also stop.

Issue: Need to implement protections against malicious codes to prevent containers running forever.

PHASE 3

Protections to be implemented:
1. Timeout - Infinite loops
2. Memory limit - prevent RAM exhaustion
3. CPU limit - prevent CPU Hogging
4. Network disabled - prevent internet access
5. Read-only filesystem - prevents file abuse
6. Container auto-remove - prevent buildup

Steps:

1. Updating docker_runner.py
2. Added limitations for CPU, RAM, disabled network access, added execution timeout and set it to 3 seconds.

ISSUE: (Resource Leak) Identified issue where for cases where execution times out the docker image still persists
Soln: Added exceptions to kill container on execution timeout. On container.wait() -> if execution time excessed EXECUTION_TIMEOUT value,
Exception is called and container is killed forcefully.



PHASE 4

Implemention Queue based execution

System:

Frontend --> FastAPI --> Redis queue --> Worker Service --> Docker Service

Exe flow:

1. User -> POST/Execute
2. API pushes job to Redis 
3. API returns job_id immediately
4. Worker pulls job 
5. Worker runs Docker container
6. Worker stores result
7. Frontend requests result

Redis setup on VM
(Fedora):

1. sudo dnf install redis
2. sudo systemctl start redis
3. sudo system ctl enable redis ( to start redis on boot )
4. redis-cli ping (verifying)
5. ip addr (get vm ip address)

Backend device setup:

1. pip install redis
2. On backed foldre create new folder 'queue' to run redis script (redis_queue.py)
3. Also create another folder 'worker' on backend folder with worker.py script
4. Create redis queue in redis_queue.py file, using rpush() and blpop() methods of redis module
5. Here blpop() blocks execution i.e., initates wait. It waits until the execution is complete and output is returned. 

On backend folder:
1. executor.py now creates jobs instead of executing them
2. main.py(API) now creates an API call (doesn't execute anything right now) instead of directly executing python.
3. worker.py fetches jobs from redis db (queue) and sends for execution and stores result in redis again as (RESULT_PREFIX + job_id, output)
4. Updated main.py to retrieve result from redis queue. 

Issue:

1. Issue where vm was hid behind host and couldnt access the vm for redis queue

Soln: 

Changed VM network settings:
1. On Adapter 1 - attach to - NAT 
2. On Adapter 2 - attach to - Host-only adapter
3. check by pinging


2. For making Fedora act like a server:

soln:
1. sudo dnf install openssh-server -y
2. sudo systemctl start sshd
3. sudo systemctl enable sshd

for allowing ssh through firewall:
1. sudo firewall-cmd --permanent --add-service=ssh
2. sudo firewall-cmd --reload

Now the VM can be accessed like a server:
1. ssh username@192.168.56.101