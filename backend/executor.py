import uuid
from queue.redis_queue import push_job

def create_job(language, code):
    
    job_id = str(uuid.uuid4())

    job = {
        "job_id": job_id,
        "language": language,
        "code": code,
        "status": "queued"
    }
    
    push_job(job)
    
    return job