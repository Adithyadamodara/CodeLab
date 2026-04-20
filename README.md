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

- Make sure to start minikube and run backend api before running commands.
Bash command to check /create-lab:
curl -X POST http://127.0.0.1:5000/create-lab \
-H "Content-Type: application/json" \
-d "{\"user\":\"adi\",\"lab_type\":\"python\"}"
powershell-
curl -Method POST http://127.0.0.1:5000/create-lab `
-Headers @{"Content-Type"="application/json"} `
-Body '{"user":"adi","lab_type":"python"}'

Verify pod creation:
kubectl get pods

Enter into created pod:
kubectl exec -it adi-python-xxxxx -- bash

Bash command to delete pod:
curl -X POST http://127.0.0.1:5000/delete-lab \
-H "Content-Type: application/json" \
-d "{\"pod_name\":\"adi-python-xxxxx\"}"  # replace xxxxx with actual number
powershell-

PHASE 3:

- Track active lab sessions
- Prevent duplicate sessions
- Store pod ownership
- Support expiry

Step 1- Start redis:
docker run -d -p 6379:6379 --name redis redis:7

verify: docker ps

Step 2- Install Redis Client:
pip install redis

Step 3- Updated app.py with redis integration

Step 4- Enforcing single session per user and with user-session id mapping 
updated create-lab in app.py
updated delete-lab in app.py

Run to check:
curl -Method POST http://127.0.0.1:5000/create-lab `
-Headers @{"Content-Type"="application/json"} `
-Body '{"user":"adi","lab_type":"python"}'

try again for same user to get error

delete lab- 
curl -Method POST http://127.0.0.1:5000/delete-lab `
-Headers @{"Content-Type"="application/json"} `
-Body '{"user":"adi"}'
