from kubernetes import client, config

config.load_kube_config()

v1 = client.CoreV1Api()

pods = v1.list_namespaced_pod(namespace="default")

for pod in pods.items:
    print(pod.metadata.name)