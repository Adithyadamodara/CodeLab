
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
