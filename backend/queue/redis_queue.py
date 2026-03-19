import redis
import json

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True
)

QUEUE_NAME = "code_jobs"

def push_job(job):
    redis_client.rpush(QUEUE_NAME, json.dumps(job))

def pop_job():
    job = redis_client.blpop(QUEUE_NAME)
    if job:
        return json.loads(job[1])