"""규칙 기반 BPMN 생성기 — 모델 없이 동작하는 최종 안전망.

로컬 LLM 이 없거나(모델 미다운로드) 로드/생성에 실패해도 코파일럿이 항상
쓸 만한 초안을 돌려주도록 한국어 키워드에서 프로세스 구조를 유추한다.

의존성이 없고 즉시(수 ms) 응답하며, 결과는 [bpmn_spec] 빌더를 통과하므로
언제나 유효한 BPMN XML 이 된다.
"""

from __future__ import annotations

from typing import Any, Dict, List

# 도메인별 단계 명칭. 프런트엔드 추천 프롬프트(관광객 혼잡 / 기상 센서 / 교통 사고)를
# 우선 다루고, 해당 없으면 범용 명칭을 사용한다.
# 각 단계에 대응하는 카탈로그 항목 이름(`*_catalog`)을 함께 둔다.
# 이 이름이 spec 의 catalogId 로 들어가면 빌더가 실행 URL 을 연결한다.
DOMAINS = [
    {
        "keys": ("관광", "혼잡", "밀집", "인파", "방문객"),
        "name": "관광지 혼잡 대응",
        "collect": "관광객 밀집도 수집",
        "collect_catalog": "관광 디지털 트윈 시뮬레이션",
        "analyze": "혼잡도 분석",
        "analyze_catalog": "관광지 쾌적지수 산출",
        "condition": "혼잡 임계 초과?",
        "action": "혼잡 완화 안내 발송",
        "action_catalog": "디지털 사이니지 표출",
        "recover": "분산 경로 안내",
        "recover_catalog": "",
    },
    {
        "keys": ("기상", "날씨", "센서", "온도", "습도", "미세먼지", "수질"),
        "name": "기상 센서 이상 대응",
        "collect": "기상 센서 데이터 수집",
        "collect_catalog": "관측 데이터 수집",
        "analyze": "센서 이상 판정",
        "analyze_catalog": "이상 탐지",
        "condition": "이상 감지?",
        "action": "이상 경보 발송",
        "action_catalog": "SMS 알림 발송",
        "recover": "복구 시나리오 실행",
        "recover_catalog": "",
    },
    {
        "keys": ("교통", "사고", "차량", "도로", "정체"),
        "name": "교통 사고 대응",
        "collect": "교통 사고 정보 수집",
        "collect_catalog": "관측 데이터 수집",
        "analyze": "사고 영향 분석",
        "analyze_catalog": "도로혼잡도 예측 엔진",
        "condition": "유관기관 통보 대상?",
        "action": "관련 기관 통합 알림",
        "action_catalog": "유관기관 통보",
        "recover": "우회 경로 안내",
        "recover_catalog": "",
    },
]

DEFAULT_DOMAIN = {
    "name": "생성된 서비스 로직",
    "collect": "데이터 수집",
    "collect_catalog": "관측 데이터 수집",
    "analyze": "데이터 분석",
    "analyze_catalog": "데이터 정제·전처리",
    "condition": "조건 충족?",
    "action": "알림 발송",
    "action_catalog": "SMS 알림 발송",
    "recover": "후속 조치 실행",
    "recover_catalog": "",
}

# 단계별 트리거 키워드
KW_COLLECT = ("수집", "센서", "데이터", "조회", "관측", "모니터", "실시간", "감시")
KW_ANALYZE = ("분석", "판단", "예측", "진단", "산출", "평가", "혼잡도", "탐지")
# "면" 한 글자는 화면/측면 등에서 오탐이 심해 조건 어미 형태로만 검사한다.
KW_CONDITION = ("감지", "이상", "초과", "임계", "발생", "조건", "판별", "여부",
                "하면", "되면", "이면", "으면", "발생 시", "경우")
KW_NOTIFY = ("알림", "경보", "통보", "전파", "안내", "통합 알림", "sms", "문자", "메시지")
KW_RECOVER = ("복구", "대응", "조치", "완화", "해소", "시나리오", "우회")
KW_STORE = ("저장", "기록", "로그", "이력", "적재")


def _pick_domain(text: str) -> Dict[str, str]:
    lowered = text.lower()
    best, score = DEFAULT_DOMAIN, 0
    for domain in DOMAINS:
        hits = sum(1 for key in domain["keys"] if key in lowered)
        if hits > score:
            best, score = domain, hits
    return best


def _has(text: str, keywords) -> bool:
    return any(k in text for k in keywords)


def build_spec(prompt: str) -> Dict[str, Any]:
    """한국어 요구사항에서 BPMN 프로세스 spec 을 구성한다."""
    text = (prompt or "").strip()
    lowered = text.lower()
    domain = _pick_domain(lowered)

    nodes: List[Dict[str, str]] = [{"id": "Start_1", "type": "startEvent", "name": "시작"}]
    flows: List[Dict[str, str]] = []
    prev = "Start_1"
    seq = 0

    def add(node_type: str, name: str, label: str = "", catalog_id: str = "") -> str:
        nonlocal prev, seq
        seq += 1
        node_id = f"Node_{seq}"
        nodes.append({"id": node_id, "type": node_type, "name": name, "catalogId": catalog_id})
        flows.append({"from": prev, "to": node_id, "name": label})
        prev = node_id
        return node_id

    # 1) 수집 — 명시되지 않아도 파이프라인의 시작으로 항상 둔다.
    add("serviceTask", domain["collect"], catalog_id=domain.get("collect_catalog", ""))

    # 2) 분석
    if _has(lowered, KW_ANALYZE) or _has(lowered, KW_COLLECT):
        add("serviceTask", domain["analyze"], catalog_id=domain.get("analyze_catalog", ""))

    # 3) 조건 분기 — 조건 신호가 있으면 게이트웨이로 두 갈래를 만든다.
    if _has(lowered, KW_CONDITION):
        gateway = add("exclusiveGateway", domain["condition"])

        seq += 1
        action_id = f"Node_{seq}"
        action_name = domain["action"] if _has(lowered, KW_NOTIFY) else domain["recover"]
        nodes.append({
            "id": action_id,
            "type": "sendTask" if _has(lowered, KW_NOTIFY) else "task",
            "name": action_name,
            "catalogId": domain.get("action_catalog", "") if _has(lowered, KW_NOTIFY)
            else domain.get("recover_catalog", ""),
        })
        flows.append({"from": gateway, "to": action_id, "name": "예"})

        # 대응 분기에 복구 단계가 더 필요한 경우
        tail = action_id
        if _has(lowered, KW_RECOVER) and _has(lowered, KW_NOTIFY):
            seq += 1
            recover_id = f"Node_{seq}"
            nodes.append({"id": recover_id, "type": "task", "name": domain["recover"]})
            flows.append({"from": action_id, "to": recover_id, "name": ""})
            tail = recover_id

        seq += 1
        normal_id = f"Node_{seq}"
        nodes.append({"id": normal_id, "type": "task", "name": "상태 기록"})
        flows.append({"from": gateway, "to": normal_id, "name": "아니오"})

        nodes.append({"id": "End_1", "type": "endEvent", "name": "종료"})
        flows.append({"from": tail, "to": "End_1", "name": ""})
        flows.append({"from": normal_id, "to": "End_1", "name": ""})
        return {"name": domain["name"], "nodes": nodes, "flows": flows}

    # 4) 분기가 없으면 선형 파이프라인
    if _has(lowered, KW_NOTIFY):
        add("sendTask", domain["action"], catalog_id=domain.get("action_catalog", ""))
    if _has(lowered, KW_RECOVER):
        add("task", domain["recover"], catalog_id=domain.get("recover_catalog", ""))
    if _has(lowered, KW_STORE):
        add("task", "결과 저장", catalog_id="결과 저장")

    nodes.append({"id": "End_1", "type": "endEvent", "name": "종료"})
    flows.append({"from": prev, "to": "End_1", "name": ""})
    return {"name": domain["name"], "nodes": nodes, "flows": flows}
