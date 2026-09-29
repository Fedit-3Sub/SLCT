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

## 4. 레지스트리 이미지로 배포 (운영)

빌드 머신에서 이미지를 만들어 레지스트리(기본 `harbor.k-sw.org/keti`)에 올리고,
배포 호스트는 `docker-compose.prod.yml` 로 받아서 실행합니다.

```bash
# 빌드 머신
./scripts/build-and-push.sh              # slct-backend · slct-frontend · slct-processor, 날짜 태그 + latest
./scripts/build-and-push.sh --no-llm     # 내장 CPU LLM(약 1.1GB) 없는 백엔드

# 배포 호스트 (docker-compose.prod.yml 과 .env 를 둔 디렉터리)
echo "DJANGO_SECRET_KEY=$(openssl rand -hex 32)" > .env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

- 프런트엔드 이미지는 빌드한 정적 파일을 nginx 로 서빙하고 `/api`·`/admin`·`/static` 을 백엔드로 넘깁니다.
- 백엔드 DB 는 `backend-data` 볼륨에 저장되어 컨테이너를 다시 만들어도 유지됩니다.
- 포트는 `SLCT_FRONTEND_PORT`·`SLCT_BACKEND_PORT`·`SLCT_PROCESSOR_PORT`, 태그는 `SLCT_TAG` 로 바꿀 수 있습니다.

## 접속 주소

| 구분 | 주소 |
| --- | --- |
| 편집기 | `http://{서버IP}:9900/{서비스로직ID}` |
| API 문서(Swagger) | `http://{서버IP}:1337/api/docs/` |
| 관리자 화면 | `http://{서버IP}:1337/admin/` |
