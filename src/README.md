# 서비스 로직 생성도구(SLCT)

**디지털 연합트윈 서비스 로직 생성 도구**는 BPMN 기반으로 서비스 로직을 설계·편집하고,
시뮬레이션 해석을 위한 로직을 효율적으로 생성하도록 지원합니다.

## 구성

| 구성 요소 | 기술 스택 | 포트 | 역할 |
|---|---|---|---|
| `frontend` | Vue 2.7 · Vite · bpmn-js (pnpm) | `9900` | BPMN 다이어그램 편집·시뮬레이션·AI 코파일럿 UI |
| `backend` | Django 5 · DRF (Python) | `1337` | 다이어그램·LLM·디지털트윈·파이프라인 REST API |
| `processor` | Flask (Python) | `9901` | BPMN 실행 요청 처리 및 실행 기록 |

프론트엔드는 `/api`로 백엔드를 호출하고, 토큰 시뮬레이션이 노드를 지날 때
해당 노드에 설정된 URL(프로세서·시뮬레이터 등)로 실행 요청을 보냅니다.

## 주요 기능

- **BPMN 다이어그램 편집** — 노드 추가·삭제·연결, XML 저장/불러오기, 속성 패널
- **토큰 시뮬레이션** — 실행 흐름을 시각화하고 단계별로 외부 엔드포인트를 호출
- **AI 코파일럿** — 자연어 요구사항으로 다이어그램 초안을 생성. 좌표가 없는 XML은
  자동 레이아웃으로 배치하며, 등록된 시뮬레이터를 지목하면 실행 URL을 함께 연결
- **노드 카탈로그** — 연합트윈 시뮬레이터·연계 서비스를 팔레트와 사이드바에서 검색·배치
- **배포 지원** — Docker Compose 및 Kubernetes 매니페스트 제공

백엔드 API 상세는 [backend/README.md](backend/README.md)를 참고하세요.

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
