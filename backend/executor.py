import uuid
from runners.docker_runner import run_python_code

def execute(language, code):

    if language == "python":
        return run_python_code(code)
    
    return "Language not supported yet"

def create_job(language, code):
    job_id = str(uuid.uuid4())

    job = {
        "job_id": job_id,
        "language": language,
        "code": code,
        "status": "queued"
    }
    
    return job