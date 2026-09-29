#!/usr/bin/env bash
# 운영 이미지 3종(backend·frontend·processor) 빌드 후 레지스트리에 올린다.
#
#   ./scripts/build-and-push.sh                  # 빌드 → 날짜 태그 + latest 푸시
#   ./scripts/build-and-push.sh --no-push        # 빌드만
#   ./scripts/build-and-push.sh --tag 20260929   # 날짜 태그 직접 지정
#   ./scripts/build-and-push.sh --no-llm         # 내장 CPU LLM 을 뺀 가벼운 백엔드 이미지
#   SLCT_REGISTRY=my.registry/proj ./scripts/build-and-push.sh
#
# 배포 호스트에서는 docker-compose.prod.yml 로 받아 실행한다.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# common.sh 의 REGISTRY 는 microk8s 로컬 레지스트리라 이름을 따로 쓴다.
REGISTRY="${SLCT_REGISTRY:-harbor.k-sw.org/keti}"
TAG=""
DO_PUSH=1
WITH_LLM=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-push) DO_PUSH=0; shift ;;
    --tag)     TAG="${2:-}"; shift 2 ;;
    --no-llm)  WITH_LLM=0; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *)         die "알 수 없는 옵션: $1" ;;
  esac
done

need docker
TAG="${TAG:-$(TZ=Asia/Seoul date +%Y%m%d)}"
VERSION="$(git -C "${SRC_DIR}" rev-parse --short HEAD 2>/dev/null || echo "${TAG}")"
HOST="${REGISTRY%%/*}"

if [[ $DO_PUSH -eq 1 ]]; then
  status=$(curl -s -o /dev/null -w "%{http_code}" "https://${HOST}/v2/" || echo "000")
  # 200 = 공개, 401 = 인증 필요(정상). 그 외는 레지스트리 장애로 본다.
  [[ "$status" == "200" || "$status" == "401" ]] || die "레지스트리(${HOST})가 응답하지 않습니다 (HTTP ${status})."
fi

build() {
  local name="$1" dir="$2"; shift 2
  local image="${REGISTRY}/slct-${name}"
  log "빌드: ${image}:${TAG}"
  docker build "$@" -t "${image}:${TAG}" -t "${image}:latest" "${dir}"
}

build backend   "${BACKEND_DIR}"   --build-arg "WITH_LOCAL_LLM=${WITH_LLM}"
build frontend  "${FRONTEND_DIR}"  --build-arg "VITE_APP_VERSION=${VERSION}"
build processor "${PROCESSOR_DIR}"

if [[ $DO_PUSH -eq 1 ]]; then
  for name in backend frontend processor; do
    image="${REGISTRY}/slct-${name}"
    log "푸시: ${image}:${TAG}, latest"
    docker push "${image}:${TAG}"
    docker push "${image}:latest"
  done
fi

log "완료 (태그 ${TAG})"
log "배포 호스트: SLCT_TAG=${TAG} docker compose -f docker-compose.prod.yml pull && ... up -d"
