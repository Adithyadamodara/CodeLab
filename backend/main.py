from fastapi import FastAPI
from models import CodeExecutionRequest
from executor import create_job

app = FastAPI()

@app.post("/execute")
def execute_code(request: CodeExecutionRequest):

    job = create_job(request.language, request.code)

    return {
        "message": "job created",
        "job id": job["job_id"]
    }
