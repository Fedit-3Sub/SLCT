#!/usr/bin/env bash
# microk8s 설치 및 배포 사전 설정 (Ubuntu 기준, sudo 권한 필요)
#  1) microk8s 설치 및 애드온(레지스트리·인그레스·저장소) 활성화
#  2) 노드 포트 범위를 9900~9910 으로 확장
#  3) kubectl 접속 정보 생성
#  4) 로컬 레지스트리(localhost:32000)를 docker 신뢰 목록에 등록
# 이미 적용된 항목은 건너뜁니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

need sudo
[ "$(id -u)" -eq 0 ] && warn "root 로 실행 중입니다. 일반 사용자로 실행하는 것을 권장합니다."

# ------------------------------------------------------------- 1. microk8s 설치
log "[1/4] microk8s 설치 및 애드온 활성화"
if ! command -v microk8s >/dev/null 2>&1; then
  need snap "Ubuntu 의 snapd 가 필요합니다."
  sudo snap install microk8s --classic
else
  log "  - microk8s 이미 설치됨"
fi
sudo microk8s status --wait-ready >/dev/null
sudo microk8s enable dashboard registry ingress hostpath-storage
log "  - 애드온 활성화 완료 (레지스트리 포트 32000)"

# ------------------------------------------------------------- 2. 노드 포트 범위
log "[2/4] 노드 포트 범위 확장 (9900-9910)"
APISERVER_ARGS=/var/snap/microk8s/current/args/kube-apiserver
PORT_RANGE_LINE='--service-node-port-range=9900-9910'
if sudo grep -q -- '--service-node-port-range=' "${APISERVER_ARGS}"; then
  log "  - 이미 설정되어 있음: $(sudo grep -- '--service-node-port-range=' "${APISERVER_ARGS}")"
else
  echo "${PORT_RANGE_LINE}" | sudo tee -a "${APISERVER_ARGS}" >/dev/null
  log "  - 설정 추가 후 microk8s 재시작"
  sudo microk8s stop && sudo microk8s start
  sudo microk8s status --wait-ready >/dev/null
fi

# ------------------------------------------------------------- 3. kubectl 설정
log "[3/4] kubectl 접속 정보 생성 (~/.kube/config)"
mkdir -p "${HOME}/.kube"
sudo microk8s config | tee "${HOME}/.kube/config" >/dev/null
chmod 600 "${HOME}/.kube/config"

# ------------------------------------------------------------- 4. 레지스트리 신뢰
log "[4/4] 로컬 레지스트리를 docker 신뢰 목록에 등록"
if command -v docker >/dev/null 2>&1; then
  DAEMON_JSON=/etc/docker/daemon.json
  sudo python3 - "${DAEMON_JSON}" "${REGISTRY}" <<'PY'
import json, os, sys
path, registry = sys.argv[1], sys.argv[2]
cfg = {}
if os.path.exists(path):
    try:
        with open(path, encoding='utf-8') as f:
            cfg = json.load(f) or {}
    except ValueError:
        print('  - 기존 daemon.json 을 해석할 수 없어 직접 확인이 필요합니다.')
        sys.exit(1)
regs = cfg.setdefault('insecure-registries', [])
if registry in regs:
    print('  - 이미 등록되어 있음')
    sys.exit(2)
regs.append(registry)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2)
print('  - %s 등록' % registry)
PY
  rc=$?
  if [ "${rc}" -eq 0 ]; then
    sudo systemctl restart docker
    log "  - docker 재시작 완료"
  elif [ "${rc}" -ne 2 ]; then
    die "daemon.json 설정에 실패했습니다."
  fi
else
  warn "docker 가 설치되어 있지 않습니다. 이미지 빌드를 위해 Docker Engine 설치가 필요합니다."
fi

log "사전 설정 완료. 배포 실행: ./scripts/deploy-microk8s.sh"
