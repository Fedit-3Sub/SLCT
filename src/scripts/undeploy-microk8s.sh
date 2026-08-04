#!/usr/bin/env bash
# microk8s 에 배포한 리소스 삭제
#  기본은 배포 리소스만 삭제하며, --all 을 주면 네임스페이스와 저장 볼륨까지 삭제합니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

if command -v kubectl >/dev/null 2>&1; then KUBECTL="kubectl"; else KUBECTL="sudo microk8s kubectl"; fi

for f in ingress processor frontend backend; do
  ${KUBECTL} delete -n "${NAMESPACE}" -f "${K8S_DIR}/${f}.yaml" --ignore-not-found
done
log "배포 리소스 삭제 완료"

if [ "${1:-}" = "--all" ]; then
  ${KUBECTL} delete namespace "${NAMESPACE}" --ignore-not-found
  log "네임스페이스(${NAMESPACE}) 및 저장 볼륨 삭제 완료"
fi
