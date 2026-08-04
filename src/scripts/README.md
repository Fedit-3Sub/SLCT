# 설치 · 실행 스크립트

Ubuntu 환경에서 서비스 로직 생성 도구(SLCT)를 설치하고 실행하는 스크립트입니다.
모든 스크립트는 소스 디렉터리(`src`)에서 실행합니다.

```bash
cd ~/SLCT/src
chmod +x scripts/*.sh
```

## 1. 개발 환경에서 실행

```bash
./scripts/setup-dev.sh     # 환경 변수 파일 생성, Node 20 · pnpm · Python 가상환경 구성
./scripts/run-dev.sh       # 프런트엔드(9900) · 백엔드(1337) · 프로세서(9901) 실행
./scripts/stop-dev.sh      # 실행 중인 3개 프로세스 종료
```

실행 로그는 `src/.run/{frontend,backend,processor}.log` 에 기록됩니다.

## 2. docker compose 로 실행

```bash
./scripts/run-docker.sh    # 3개 컨테이너 빌드 및 실행
./scripts/stop-docker.sh   # 컨테이너 정지 및 삭제
```

## 3. microk8s 로 배포

```bash
./scripts/setup-microk8s.sh      # microk8s 설치, 애드온, 노드 포트 범위, 레지스트리 신뢰 설정
./scripts/deploy-microk8s.sh     # 이미지 빌드 → 레지스트리 푸시 → 배포
./scripts/undeploy-microk8s.sh   # 배포 리소스 삭제 (--all 은 네임스페이스까지 삭제)
```

## 접속 주소

| 구분 | 주소 |
| --- | --- |
| 편집기 | `http://{서버IP}:9900/{서비스로직ID}` |
| API 문서(Swagger) | `http://{서버IP}:1337/api/docs/` |
| 관리자 화면 | `http://{서버IP}:1337/admin/` |
