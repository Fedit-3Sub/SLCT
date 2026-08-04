#!/usr/bin/env bash
# 설치·실행 스크립트 공통 함수 및 경로 정의
# (각 스크립트에서 source 하여 사용)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"      # 소스 디렉터리(src)
LOG_DIR="${SRC_DIR}/.run"                       # 실행 로그 및 PID 파일 보관

FRONTEND_DIR="${SRC_DIR}/frontend"
BACKEND_DIR="${SRC_DIR}/backend"
PROCESSOR_DIR="${SRC_DIR}/processor"
K8S_DIR="${SRC_DIR}/k8s"

REGISTRY="localhost:32000"                      # microk8s 로컬 레지스트리
NAMESPACE="kt-bpmn"                             # 쿠버네티스 네임스페이스

log()  { printf '\033[1;32m[%s]\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; }
warn() { printf '\033[1;33m[%s] 주의:\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; }
die()  { printf '\033[1;31m[%s] 오류:\033[0m %s\n' "$(date '+%H:%M:%S')" "$*" >&2; exit 1; }

# 필수 명령 존재 확인
need() {
  command -v "$1" >/dev/null 2>&1 || die "$1 명령을 찾을 수 없습니다. ${2:-먼저 설치한 뒤 다시 실행하세요.}"
}

# fnm(Node 버전 관리자)을 현재 셸에서 사용할 수 있도록 준비
load_node() {
  if ! command -v fnm >/dev/null 2>&1; then
    for d in "${HOME}/.local/share/fnm" "${HOME}/.fnm"; do
      [ -x "${d}/fnm" ] && export PATH="${d}:${PATH}"
    done
  fi
  command -v fnm >/dev/null 2>&1 && eval "$(fnm env --use-on-cd)" || true
}
