from flask import Flask, request, jsonify
from kubernetes import client, config
from datetime import datetime, timedelta
import uuid
import redis
import json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

app = Flask(__name__)

config.load_kube_config()
v1 = client.CoreV1Api()

# 🔹 Create Lab
@app.route("/create-lab", methods=["POST"])
def create_lab():
    data = request.json

    user = data.get("user", "guest")
    lab_type = data.get("lab_type", "python")

    # Preventing multiple sessions per user
    if r.exists(f"user:{user}:session"):
        return jsonify({"error":"User already has active lab"}), 400 

    # Session id
    session_id = str(uuid.uuid4()) 
    pod_name = f"{user}-{lab_type}-{str(uuid.uuid4())[:5]}"

    container = client.V1Container(
        name="lab-container",
        image="python-lab",
        image_pull_policy="Never",
        command=["sleep", "3600"],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "200m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"}
        )
    )

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=pod_name),
        spec=client.V1PodSpec(
            containers=[container],
            restart_policy="Never"
        )
    )

    v1.create_namespaced_pod(namespace="default", body=pod)

    # Storing session data
    session_data = {
        "user":user,
        "pod_name":pod_name,
        "lab_type":lab_type,
        "start_time":str(datetime.utcnow()),
        "status": "running"
    }

    r.set(f"session:{session_id}", json.dumps(session_data))
    r.set(f"user:{user}:session", session_id)
    
    # Setting TTL 15 mins
    r.expire(f"session:{session_id}", 900)

    return jsonify({
        "message": "Lab created",
        "pod_name": pod_name
    })

# 🔹 Delete Lab
@app.route("/delete-lab", methods=["POST"])
def delete_lab():
    data = request.json
    user = data.get("user")
    
    session_id = r.get(f"user:{user}:session")

    if not session_id:
        return jsonify({"error":"No active session"}), 400

    session_data = json.loads(r.get(f"session:{session_id}"))
    pod_name = session_data["pod_name"]

    v1.delete_namespaced_pod(name=pod_name, namespace="default")

    r.delete(f"session:{session_id}")
    r.delete(f"user:{user}:session")

    return jsonify({"message": "Lab deleted"})


if __name__ == "__main__":
    app.run(debug=True)