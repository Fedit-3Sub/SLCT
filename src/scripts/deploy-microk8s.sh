#!/usr/bin/env bash
# 이미지 빌드 → 로컬 레지스트리 푸시 → microk8s 배포
#  사전 조건: ./scripts/setup-microk8s.sh 실행 완료
#  삭제는 ./scripts/undeploy-microk8s.sh 를 사용합니다.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

need docker
if command -v kubectl >/dev/null 2>&1; then KUBECTL="kubectl"; else KUBECTL="sudo microk8s kubectl"; fi

# ------------------------------------------------------------- 1. 이미지 빌드
log "[1/3] 컨테이너 이미지 빌드"
for c in backend frontend processor; do
  d="${SRC_DIR}/${c}"
  # 각 Dockerfile 이 .env 를 복사하므로 없으면 샘플에서 생성한다.
  if [ ! -f "${d}/.env" ]; then
    sample="$(ls "${d}"/.env.example "${d}"/.env-sample 2>/dev/null | head -1 || true)"
    if [ -n "${sample}" ]; then cp "${sample}" "${d}/.env"; else : > "${d}/.env"; fi
    log "  - ${c}/.env 생성"
  fi
  log "  - ${c} 이미지 빌드"
  ( cd "${SRC_DIR}" && docker build -t "${REGISTRY}/bpmn-${c}:latest" -f "./${c}/Dockerfile" "./${c}" )
done

# ------------------------------------------------------------- 2. 레지스트리 푸시
log "[2/3] 로컬 레지스트리(${REGISTRY}) 푸시"
for c in frontend backend processor; do
  docker push "${REGISTRY}/bpmn-${c}:latest"
done

# ------------------------------------------------------------- 3. 배포
log "[3/3] 쿠버네티스 배포 (네임스페이스: ${NAMESPACE})"
${KUBECTL} get namespace "${NAMESPACE}" >/dev/null 2>&1 || ${KUBECTL} create namespace "${NAMESPACE}"
${KUBECTL} config set-context --current --namespace="${NAMESPACE}" >/dev/null

for f in backend frontend processor ingress; do
  ${KUBECTL} apply -n "${NAMESPACE}" -f "${K8S_DIR}/${f}.yaml"
done

log "배포 진행 상태 확인 (최대 3분 대기)"
for d in bpmn-backend-deployment bpmn-frontend-deployment bpmn-processor-deployment; do
  ${KUBECTL} rollout status -n "${NAMESPACE}" "deployment/${d}" --timeout=180s \
    || warn "${d} 준비가 지연되고 있습니다. '${KUBECTL} get pods -n ${NAMESPACE}' 로 상태를 확인하세요."
done

${KUBECTL} get pods,svc -n "${NAMESPACE}"
log "접속 주소: http://{서버IP}:9900/{서비스로직ID}"
