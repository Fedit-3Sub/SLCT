# 서비스 로직 생성도구(SLCT)

프론트엔드(Vue, `9900`) · 백엔드(Django, `1337`) · 프로세서(Flask, `9901`) 3-tier 구성입니다.
개요와 빠른 시작은 루트 [README.md](../README.md), 백엔드 API 상세는 [backend/README.md](backend/README.md)를 참고하세요.

## Docker Compose

각 서비스는 `.env`를 읽습니다. 최초 1회 샘플을 복사한 뒤 실행하세요.

```bash
cp backend/.env.example  backend/.env
cp frontend/.env-sample  frontend/.env
cp processor/.env-sample processor/.env

docker compose up --build -d
```

## Kubernetes (microk8s)

### 설치

```bash
sudo snap install microk8s --classic
microk8s status --wait-ready
microk8s enable dashboard registry ingress
microk8s kubectl get all --all-namespaces

mkdir -p ~/.kube && microk8s config > ~/.kube/config
```

낮은 대역 NodePort(9900~9910)를 허용하려면:

```bash
# /var/snap/microk8s/current/args/kube-apiserver 에 추가
--service-node-port-range=9900-9910

microk8s stop && microk8s start
```

### 이미지 빌드 & 푸시

```bash
docker build -t localhost:32000/bpmn-backend:latest   -f ./backend/Dockerfile   ./backend
docker build -t localhost:32000/bpmn-frontend:latest  -f ./frontend/Dockerfile  ./frontend
docker build -t localhost:32000/bpmn-processor:latest -f ./processor/Dockerfile ./processor

# 로컬 레지스트리 사용 시 /etc/docker/daemon.json 에
#   { "insecure-registries": ["localhost:32000"] }
# 추가 후 `sudo systemctl restart docker`

docker push localhost:32000/bpmn-backend:latest
docker push localhost:32000/bpmn-frontend:latest
docker push localhost:32000/bpmn-processor:latest
```

### 배포

```bash
kubectl create namespace kt-bpmn
kubectl config set-context --current --namespace=kt-bpmn
kubectl apply -f ./k8s/backend.yaml
kubectl apply -f ./k8s/frontend.yaml
kubectl apply -f ./k8s/processor.yaml
kubectl apply -f ./k8s/ingress.yaml
```

포트 포워딩:

```bash
nohup kubectl -n kt-bpmn port-forward service/bpmn-frontend-service  --address=0.0.0.0 9900:9900 &
nohup kubectl -n kt-bpmn port-forward service/bpmn-processor-service --address=0.0.0.0 9901:9901 &
kubectl -n kt-bpmn port-forward service/bpmn-backend-service --address=0.0.0.0 1337:1337
```

## 로컬 개발

### 프론트엔드 (Node 18+, pnpm)
```bash
cd frontend
pnpm install && pnpm dev
```

### 백엔드 (Python, Django)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver        # 0.0.0.0:1337
```

### 프로세서 (Python, Flask)
```bash
cd processor
pip install -r requirements.txt
python3 main.py                   # 0.0.0.0:9901
```

## 사용

```
http://localhost:9900/<다이어그램id>
```
