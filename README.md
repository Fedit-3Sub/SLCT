# KT-BPMN

## docker compose

### 설치

docker compose

### 실행
```
docker compose up --build -d
```

## kubernates (minikube)

### 설치
minikube

```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64

minikube start
minikube dashboard
```

build docker image
```
eval $(minikube docker-env)
docker build -t bpmn-backend:latest -f ./backend/Dockerfile ./backend
docker build -t bpmn-frontend:latest -f ./frontend/Dockerfile ./frontend
docker build -t bpmn-processor:latest -f ./processor/Dockerfile ./processor
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
```

port forwarding
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

