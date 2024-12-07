# SLCT
4)서비스 로직 생성엔진 기술 개발

---------------------------------------
# 서비스 로직 생성 도구

> **디지털 연합트윈 서비스 로직 생성 도구**는 bpmn 기반의 서비스 로직을 생성하는 작업을 지원하며, 시뮬레이션 해석을 위한 효율적인 로직 생성 도구를 제공합니다.


## 주요 기능
- **BPMN 다이어그램 편집**: 노드 추가, 삭제, 연결을 지원하며 XML 형식으로 저장/불러오기 가능.
- **로직 시뮬레이션**: 실행 흐름 테스트 및 결과 로그 확인.
- **API 연동**: 디지털 트윈 메타데이터를 활용한 동적 로직 생성.
- **배포 지원**: Docker 및 Kubernetes를 통한 확장성과 안정성 확보.

---

## 📋 사용 예제

### BPMN 로직 생성 및 시뮬레이션
- 프론트엔드에서 BPMN 다이어그램을 생성.
- 노드 간 연결 설정 후 저장.
- 로직 시뮬레이션 실행 및 로그 확인.

---

## 🛠️ 프로젝트 구조
- **frontend**: BPMN 다이어그램 기반의 프론트엔드 UI.
- **backend**: Strapi를 활용한 데이터 관리 및 API 서버.
- **processor**: Python 기반의 데이터 처리 모듈.
- **k8s**: Kubernetes 배포를 위한 YAML 설정 파일.

---

## 🛠️ 개발 환경

### 의존성 설치
**Node.js 설치**:
```bash
curl -fsSL https://fnm.vercel.app/install | bash
fnm use --install-if-missing 20
corepack enable
```

**파이썬 패키지 설치**
```bash
pip3 install -r ./processor/requirements.txt
```

### 개발 환경 실행
- **백엔드 실행**
```bash
cd backend
npm install
npm run develop
```

- **프론트엔드 실행**:
 ```bash
cd frontend
pnpm install
pnpm dev
```

---

## 🛠️ 배포
- **Docker Compose를 활용한 배포**
```bash
docker compose up --build -d
```

- **Kubernetes를 활용한 배포**:
1. microK8S 설치
  ```bash
  sudo snap install microk8s --classic
  microk8s enable dashboard registry ingress
  ```

2. Docker image 빌드 및 푸쉬
  ```bash
    docker build -t localhost:32000/bpmn-backend:latest -f ./backend/Dockerfile ./backend
    docker build -t localhost:32000/bpmn-frontend:latest -f ./frontend/Dockerfile ./frontend
    docker build -t localhost:32000/bpmn-processor:latest -f ./processor/Dockerfile ./processor
    
    /etc/docker/daemon.json
    {
    "insecure-registries" : ["localhost:32000"]
    }
    sudo systemctl restart docker
    
    docker push localhost:32000/bpmn-frontend:latest
    docker push localhost:32000/bpmn-backend:latest
    docker push localhost:32000/bpmn-processor:latest
  ```

3. 빌드 이미지 배포
  ```bash
   kubectl create namespace kt-bpmn
   kubectl config set-context --current --namespace=kt-bpmn
   kubectl config view --minify | grep namespace
   kubectl apply -f ./k8s/backend.yaml
   kubectl apply -f ./k8s/frontend.yaml
   kubectl apply -f ./k8s/processor.yaml
   kubectl apply -f ./k8s/ingress.yaml
  ```




