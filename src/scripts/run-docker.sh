#!/usr/bin/env bash
# docker compose 를 이용한 서버 실행 (프런트엔드 9900 / 백엔드 1337 / 프로세서 9901)
#  - 환경 변수 파일이 없으면 샘플에서 자동 생성합니다.
#  - 종료는 ./scripts/stop-docker.sh 를 사용합니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

need docker "Docker Engine 을 설치한 뒤 다시 실행하세요."
docker compose version >/dev/null 2>&1 || die "docker compose(v2) 를 사용할 수 없습니다."

# 컨테이너 빌드 시 각 Dockerfile 이 .env 를 복사하므로 반드시 존재해야 한다.
for d in "${BACKEND_DIR}" "${FRONTEND_DIR}" "${PROCESSOR_DIR}"; do
  if [ ! -f "${d}/.env" ]; then
    sample="$(ls "${d}"/.env.example "${d}"/.env-sample 2>/dev/null | head -1 || true)"
    if [ -n "${sample}" ]; then cp "${sample}" "${d}/.env"; else : > "${d}/.env"; fi
    log "$(basename "${d}")/.env 생성"
  fi
done

# 컨테이너에서 백엔드를 찾을 수 있도록 호스트 게이트웨이 주소를 사용한다.
if [ -f "${FRONTEND_DIR}/.env" ] && grep -q '^VITE_PROXY_URL=http://localhost:1337' "${FRONTEND_DIR}/.env"; then
  sed -i 's|^VITE_PROXY_URL=http://localhost:1337|VITE_PROXY_URL=http://host.docker.internal:1337|' \
    "${FRONTEND_DIR}/.env"
  log "frontend/.env 의 백엔드 주소를 http://host.docker.internal:1337 로 조정"
fi

log "컨테이너 이미지 빌드 및 실행"
( cd "${SRC_DIR}" && docker compose up --build -d )

log "실행 상태"
( cd "${SRC_DIR}" && docker compose ps )

log "접속 주소: http://localhost:9900/{서비스로직ID}"
log "로그 확인: cd ${SRC_DIR} && docker compose logs -f"
log "종료     : ./scripts/stop-docker.sh"
