#!/usr/bin/env bash
# 개발 환경 일괄 구성 스크립트 (Ubuntu 기준)
#  1) 환경 변수 파일(.env) 생성
#  2) Node.js 20 LTS 및 pnpm 설치 후 프런트엔드 의존 패키지 설치
#  3) 백엔드/프로세서 Python 가상환경 생성 및 패키지 설치, 데이터베이스 초기화
# 이미 구성된 항목은 건너뛰므로 여러 번 실행해도 안전합니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "소스 디렉터리: ${SRC_DIR}"

# ------------------------------------------------------------- 1. 환경 변수 파일
log "[1/4] 환경 변수 파일(.env) 확인"
copy_env() {
  local sample="$1" target="$2"
  if [ -f "${target}" ]; then
    log "  - $(basename "$(dirname "${target}")")/.env 이미 존재 (그대로 사용)"
  elif [ -f "${sample}" ]; then
    cp "${sample}" "${target}"
    log "  - $(basename "$(dirname "${target}")")/.env 생성"
  else
    : > "${target}"
    log "  - $(basename "$(dirname "${target}")")/.env 빈 파일 생성 (샘플 없음)"
  fi
}
copy_env "${BACKEND_DIR}/.env.example"   "${BACKEND_DIR}/.env"
copy_env "${FRONTEND_DIR}/.env-sample"   "${FRONTEND_DIR}/.env"
copy_env "${PROCESSOR_DIR}/.env-sample"  "${PROCESSOR_DIR}/.env"

# 개발 환경에서 직접 실행하는 경우 백엔드는 localhost:1337 로 접근해야 한다.
if grep -q '^VITE_PROXY_URL=http://host.docker.internal:1337' "${FRONTEND_DIR}/.env" 2>/dev/null; then
  sed -i 's|^VITE_PROXY_URL=http://host.docker.internal:1337|VITE_PROXY_URL=http://localhost:1337|' \
    "${FRONTEND_DIR}/.env"
  log "  - frontend/.env 의 백엔드 주소를 http://localhost:1337 로 조정"
fi

# ------------------------------------------------------------- 2. Node.js / pnpm
log "[2/4] Node.js 20 LTS 및 pnpm 준비"
load_node
if ! command -v fnm >/dev/null 2>&1; then
  need curl
  log "  - fnm(Fast Node Manager) 설치"
  curl -fsSL https://fnm.vercel.app/install | bash >/dev/null
  load_node
fi
command -v fnm >/dev/null 2>&1 || die "fnm 설치에 실패했습니다. 터미널을 새로 열고 다시 실행해 보세요."
fnm use --install-if-missing 20
corepack enable >/dev/null 2>&1 || warn "corepack enable 실패 (권한 문제일 수 있습니다)"
log "  - Node $(node -v) 사용"

log "  - 프런트엔드 의존 패키지 설치 (수 분 소요)"
( cd "${FRONTEND_DIR}" && pnpm install )

# ------------------------------------------------------------- 3. 백엔드(Python)
log "[3/4] 백엔드 가상환경 구성 및 데이터베이스 초기화"
need python3
[ -d "${BACKEND_DIR}/.venv" ] || python3 -m venv "${BACKEND_DIR}/.venv"
"${BACKEND_DIR}/.venv/bin/pip" install --upgrade pip >/dev/null
"${BACKEND_DIR}/.venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
( cd "${BACKEND_DIR}" && "${BACKEND_DIR}/.venv/bin/python" manage.py migrate )

# ------------------------------------------------------------- 4. 프로세서(Python)
log "[4/4] 파이프라인 프로세서 가상환경 구성 (패키지가 크므로 시간이 걸립니다)"
[ -d "${PROCESSOR_DIR}/.venv" ] || python3 -m venv "${PROCESSOR_DIR}/.venv"
"${PROCESSOR_DIR}/.venv/bin/pip" install --upgrade pip >/dev/null
"${PROCESSOR_DIR}/.venv/bin/pip" install -r "${PROCESSOR_DIR}/requirements.txt"

log "개발 환경 구성 완료. 서버 실행: ./scripts/run-dev.sh"
