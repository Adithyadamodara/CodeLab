Phase 1:

 - Build a lab container image
 - Run it inside Kubernetes (Minikube)
 - Apply CPU + memory limits
 - Verify it is actually working

Using Minikube's Docker (Important):
minikube docker-env | Invoke-Expression

verify:
docker ps

Created Dockerfile in python-lab folder and built image:
docker build -t python-lab .
docker images

after creating image:
kubectl run python-lab-test --image=python-lab --restart=Never --image-pull-policy=Never

verify:
kubectl get pods

execute and enter bash terminal:
kubectl exec -it python-lab-test -- bash

terminal should enter:
root@python-lab-test:/workspace#

Create python-lab-pod.yaml file to test on resource constraints
After creating .yaml file:
kubectl apply -f python-lab-pod.yaml
kubeclt get pods

Verify using:
kubectl describe pod python-lab-test



PHASE 2:

- Backend flask api controlling kubernetes
- Pod creation and deletion via api
- Resource constraints in place

Bash command to check /create-lab:
curl -X POST http://127.0.0.1:5000/create-lab \
-H "Content-Type: application/json" \
-d "{\"user\":\"adi\",\"lab_type\":\"python\"}"

Bash command to delete pod:
curl -X POST http://127.0.0.1:5000/delete-lab \
-H "Content-Type: application/json" \
-d "{\"pod_name\":\"adi-python-xxxxx\"}"  # replace xxxxx with actual number