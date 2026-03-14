import uuid

def create_job(language, code):
    job_id = str(uuid.uuid4())

    job = {
        "job_id": job_id,
        "language": language,
        "code": code,
        "status": "queued"
    }
    
    return job