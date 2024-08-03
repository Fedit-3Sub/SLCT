# KT-BPMN

## docker compose

### 설치

docker compose

### 실행
```
docker compose up --build -d
```

## kubernates ()

### 설치
microk8s

```
sudo snap install microk8s --classic
microk8s status --wait-ready
microk8s enable dashboard
microk8s enable registry
microk8s enable ingress
microk8s kubectl get all --all-namespaces
microk8s dashboard-proxy

rm -rf ~/.kube
mkdir ~/.kube
cd ~/.kube
microk8s config > config
```

enable low range node ports
```
vi /var/snap/microk8s/current/args/kube-apiserver
...
--service-node-port-range=9900-9910

microk8s stop
microk8s start
```

build docker images
```
docker build -t bpmn-backend:latest -f ./backend/Dockerfile ./backend
docker build -t bpmn-frontend:latest -f ./frontend/Dockerfile ./frontend
docker build -t bpmn-processor:latest -f ./processor/Dockerfile ./processor

import docker images (microk8s)
```
docker save bpmn-backend > bpmn-backend.tar
microk8s ctr image import bpmn-backend.tar

docker save bpmn-frontend > bpmn-frontend.tar
microk8s ctr image import bpmn-frontend.tar

docker save bpmn-processor > bpmn-processor.tar
microk8s ctr image import bpmn-processor.tar
```

### 실행
kubectl deployment & service
```
kubectl create namespace kt-bpmn
kubectl config set-context --current --namespace=kt-bpmn
kubectl config view --minify | grep namespace
kubectl apply -f ./k8s/backend.yaml
kubectl apply -f ./k8s/frontend.yaml
kubectl apply -f ./k8s/processor.yaml
kubectl apply -f ./k8s/ingress.yaml
```

port forwarding (minikube)
```
nohup kubectl -n kt-bpmn port-forward service/bpmn-frontend-service --address=0.0.0.0 9900:9900 &
nohup kubectl -n kt-bpmn port-forward service/bpmn-processor-service --address=0.0.0.0 9901:9901 &
```

## local development

### 설치

nodejs
```
curl -fsSL https://fnm.vercel.app/install | bash
fnm use --install-if-missing 20
corepack enable
```

python
```
pip3 install -r ./processor/requirements.txt
```

### 실행

```
cd frontend
pnpm i && pnpm dev
```

```
cd backend
* edit .env
npm i && npm run develop
```

```
cd processor
python3 main.py
```

## 설정

ssl port forward 1337, 9000

strapi admin
http://localhost:1337

```
email: admin@keti.re.kr
password: ketiKeti!@34
```

## 사용

http://localhost:9900/[다이어그램id]

