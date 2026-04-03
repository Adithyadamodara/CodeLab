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