from flask import Flask, request, jsonify
from kubernetes import client, config
import uuid

app = Flask(__name__)

config.load_kube_config()
v1 = client.CoreV1Api()

# 🔹 Create Lab
@app.route("/create-lab", methods=["POST"])
def create_lab():
    data = request.json
    user = data.get("user", "guest")
    lab_type = data.get("lab_type", "python")

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

    return jsonify({
        "message": "Lab created",
        "pod_name": pod_name
    })


# 🔹 Delete Lab
@app.route("/delete-lab", methods=["POST"])
def delete_lab():
    data = request.json
    pod_name = data.get("pod_name")

    v1.delete_namespaced_pod(name=pod_name, namespace="default")

    return jsonify({"message": f"{pod_name} deleted"})


if __name__ == "__main__":
    app.run(debug=True)