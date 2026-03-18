from queue.redis_queue import pop_job
from runners.docker_runner import run_python_code

import redis
import json

redis_client = redis.Redis(
    host="10.0.2.15",
    port=6379,
    decode_responses=True
)

RESULT_PREFIX = "result:"

def store_result(job_id, output):
    redis_client.set(RESULT_PREFIX + job_id, output)

while True:
    job = pop_job()

    print("Processing job:", job["job_id"])

    if job["language"] == "python":
        output = run_python_code(job["code"])
    else:
        output = "Unsupported language"

    store_result(job["job_id"], output)
