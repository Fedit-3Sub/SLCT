#!/usr/bin/env bash
# run-dev.sh 로 실행한 개발 서버(프런트엔드/백엔드/프로세서) 종료

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

for name in frontend backend processor; do
  pidfile="${LOG_DIR}/${name}.pid"
  if [ -f "${pidfile}" ]; then
    pid="$(cat "${pidfile}")"
    if kill -0 "${pid}" 2>/dev/null; then
      # 자식 프로세스(vite 등)까지 함께 종료
      pkill -P "${pid}" 2>/dev/null || true
      kill "${pid}" 2>/dev/null || true
      log "${name} 종료 (PID ${pid})"
    else
      log "${name} 은(는) 실행 중이 아닙니다"
    fi
    rm -f "${pidfile}"
  else
    log "${name} 실행 기록이 없습니다"
  fi
done
