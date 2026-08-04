#!/usr/bin/env bash
# docker compose 로 실행한 컨테이너 정지 및 삭제

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

need docker
log "컨테이너 정지 및 삭제"
( cd "${SRC_DIR}" && docker compose down )
log "완료"
