from fastapi import FastAPI
from models import CodeExecutionRequest
from executor import create_job
import redis

app = FastAPI()

redis_client = redis.Redis(
    host="10.0.2.15",
    port="6379",
    decode_responses=True
)

@app.post("/execute")
def execute_code(request: CodeExecutionRequest):

    job_id = create_job(request.language, request.code)
    
    return {
        "message": "job queued",
        "job_id": job_id
    }


@app.get("/result/{job_id}")
def get_result(job_id):

    result = redis_client.get("result:" + job_id)
    
    if result:
        return { "output": result }

    return { "status" : "processing" }