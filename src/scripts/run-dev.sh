#!/usr/bin/env bash
# 개발 환경에서 3개 구성요소(프런트엔드 9900 / 백엔드 1337 / 프로세서 9901)를 한 번에 실행
#  - 각 프로세스는 백그라운드로 실행되며 로그는 src/.run/*.log 에 기록됩니다.
#  - 종료는 ./scripts/stop-dev.sh 를 사용합니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

mkdir -p "${LOG_DIR}"
load_node

start() {                       # start <이름> <작업 디렉터리> <명령...>
  local name="$1" dir="$2"; shift 2
  local pidfile="${LOG_DIR}/${name}.pid"
  if [ -f "${pidfile}" ] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
    warn "${name} 은(는) 이미 실행 중입니다 (PID $(cat "${pidfile}"))"
    return 0
  fi
  ( cd "${dir}" && nohup "$@" > "${LOG_DIR}/${name}.log" 2>&1 & echo $! > "${pidfile}" )
  log "${name} 실행 (PID $(cat "${pidfile}"), 로그: .run/${name}.log)"
}

[ -d "${BACKEND_DIR}/.venv" ]   || die "백엔드 가상환경이 없습니다. 먼저 ./scripts/setup-dev.sh 를 실행하세요."
[ -d "${PROCESSOR_DIR}/.venv" ] || die "프로세서 가상환경이 없습니다. 먼저 ./scripts/setup-dev.sh 를 실행하세요."

start backend   "${BACKEND_DIR}"   "${BACKEND_DIR}/.venv/bin/python"   manage.py runserver 0.0.0.0:1337
start processor "${PROCESSOR_DIR}" "${PROCESSOR_DIR}/.venv/bin/python" main.py
start frontend  "${FRONTEND_DIR}"  pnpm dev

log "접속 주소"
log "  편집기      : http://localhost:9900/{서비스로직ID}"
log "  API 문서    : http://localhost:1337/api/docs/"
log "  관리자 화면 : http://localhost:1337/admin/"
log "종료: ./scripts/stop-dev.sh"
