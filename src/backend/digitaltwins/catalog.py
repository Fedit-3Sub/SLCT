"""연합트윈 시뮬레이터·서비스 카탈로그 (오프라인 기본값).

연합트윈 메타데이터 API 에 연결할 수 없거나 인증 토큰이 없는 환경에서도
BPMN 노드 팔레트와 통합 검색이 의미 있는 항목을 보여주도록 하는 기본 목록이다.

항목 구성은 실제 연계 자료를 따른다.
- 디지털트윈 식별자 형식: `KR-02-K10000-20240001` (환경 디지털 트윈)
- 시뮬레이션 조회 경로: `/meta/api/v1/resource/simulations/{simulationId}`
- 메타데이터 속성명이 표준 모델과 다른 경우가 있다(예: name → simulationName)

토큰이 설정되면 [fedit_client] 가 실제 메타데이터를 우선 사용하고,
이 목록은 연결 실패 시의 대체 자료로만 쓰인다.
"""

from __future__ import annotations

from typing import Any, Dict, List

# 연합트윈 구성요소 기본 주소. 환경에 따라 접근이 제한될 수 있어
# 노드에는 주소를 함께 담아두고 실제 호출 가능 여부는 실행 시점에 판단한다.
FEDIT_ENDPOINTS = {
    "metadata": "http://220.124.222.86:16997",
    "twin_search": "http://220.124.222.86:8084/meta/exsearch/list",
    "predictor": "http://220.124.222.82:18080",
    "discrete_simulator": "http://220.124.222.89",
    "portal": "https://service.fedit.or.kr",
}

# 디지털 트윈 및 시뮬레이션 카탈로그.
#   twin        : 소속 디지털 트윈
#   twin_id     : 디지털트윈 식별자(형식 예시 포함)
#   category    : 분류(팔레트 그룹)
#   url         : 시뮬레이션 실행 요청 경로
#   provider    : 제공 기관
SIMULATIONS: List[Dict[str, Any]] = [
    # --- 환경 디지털 트윈 -------------------------------------------------
    {
        "name": "환경 디지털 트윈 미세먼지 예측시뮬레이션",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "이에이트",
        "description": "기상·대기 관측값을 입력받아 미세먼지 농도를 예측한다.",
        "inputs": ["관측시각", "지역코드", "풍향", "풍속", "기온", "습도"],
        "outputs": ["PM10", "PM2.5", "예측등급"],
        "url": "/api/pipelines/run?id=env-pm-forecast",
    },
    {
        "name": "대기환경 시뮬레이션",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "네트로",
        "description": "풍향·풍속 자료를 이용한 대기 확산 시뮬레이션.",
        "inputs": ["wind.json", "격자정보", "배출원"],
        "outputs": ["airSimul.out", "확산농도장"],
        "url": "/api/pipelines/run?id=air-quality-sim",
    },
    {
        "name": "미세먼지 시뮬레이터 엔진",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "이에이트",
        "description": "미세먼지 확산 및 저감 시나리오 시뮬레이션 엔진.",
        "inputs": ["시나리오ID", "저감조치"],
        "outputs": ["시간별 농도", "저감효과"],
        "url": "/api/pipelines/run?id=pm-engine",
    },
    # --- 관광 디지털 트윈 -------------------------------------------------
    {
        "name": "관광 디지털 트윈 시뮬레이션",
        "twin": "관광 디지털 트윈",
        "twin_id": "KR-02-K10000-20240002",
        "category": "관광",
        "provider": "이에이트",
        "description": "관광지 방문객 유동을 시뮬레이션한다.",
        "inputs": ["관광지코드", "기간", "기상조건"],
        "outputs": ["방문객수", "체류시간", "혼잡도"],
        "url": "/api/pipelines/run?id=tour-flow",
    },
    {
        "name": "관광지 쾌적지수 산출",
        "twin": "관광 디지털 트윈",
        "twin_id": "KR-02-K10000-20240002",
        "category": "관광",
        "provider": "ETRI",
        "description": "혼잡도·기상·대기질을 종합해 관광지 쾌적지수를 산출한다.",
        "inputs": ["혼잡도", "기온", "미세먼지"],
        "outputs": ["쾌적지수", "권고등급"],
        "url": "/api/pipelines/run?id=tour-comfort",
    },
    # --- 교통 디지털 트윈 -------------------------------------------------
    {
        "name": "도로혼잡도 예측 엔진",
        "twin": "교통 디지털 트윈",
        "twin_id": "KR-02-K10000-20240003",
        "category": "교통",
        "provider": "ETRI",
        "description": "구간별 교통량을 입력받아 혼잡도를 예측한다.",
        "inputs": ["도로구간ID", "시간대", "교통량"],
        "outputs": ["혼잡등급", "예상통행시간"],
        "url": "/api/pipelines/run?id=road-congestion",
    },
    {
        "name": "주차장 혼잡도 예측 엔진",
        "twin": "교통 디지털 트윈",
        "twin_id": "KR-02-K10000-20240003",
        "category": "교통",
        "provider": "ETRI",
        "description": "주차장 점유율 추이를 학습해 혼잡도를 예측한다.",
        "inputs": ["주차장ID", "시간대", "현재점유율"],
        "outputs": ["예측점유율", "혼잡등급"],
        "url": "/api/pipelines/run?id=parking-congestion",
    },
    {
        "name": "교통 이산사건 시뮬레이터",
        "twin": "교통 디지털 트윈",
        "twin_id": "KR-02-K10000-20240003",
        "category": "교통",
        "provider": "연합트윈",
        "description": "신호·차량 흐름을 이산사건 방식으로 모사한다.",
        "inputs": ["네트워크", "신호계획", "수요"],
        "outputs": ["지체시간", "대기행렬"],
        "url": "/api/pipelines/run?id=discrete-traffic",
    },
    # --- 방재/안전 --------------------------------------------------------
    {
        "name": "침수 예측 시뮬레이션",
        "twin": "방재 디지털 트윈",
        "twin_id": "KR-02-K10000-20240004",
        "category": "방재",
        "provider": "연합트윈",
        "description": "강우량과 지형을 이용해 침수 범위를 예측한다.",
        "inputs": ["강우량", "지형고도", "배수능력"],
        "outputs": ["침수심", "침수범위"],
        "url": "/api/pipelines/run?id=flood-forecast",
    },
    {
        "name": "재난 대피 시뮬레이션",
        "twin": "방재 디지털 트윈",
        "twin_id": "KR-02-K10000-20240004",
        "category": "방재",
        "provider": "연합트윈",
        "description": "인구 분포 기반 대피 경로와 소요시간을 산출한다.",
        "inputs": ["인구분포", "대피소위치", "재난유형"],
        "outputs": ["대피경로", "대피소요시간"],
        "url": "/api/pipelines/run?id=evacuation-sim",
    },
    # --- 에너지 -----------------------------------------------------------
    {
        "name": "전력 수요 예측",
        "twin": "에너지 디지털 트윈",
        "twin_id": "KR-02-K10000-20240005",
        "category": "에너지",
        "provider": "연합트윈",
        "description": "기상과 사용 이력을 이용해 전력 수요를 예측한다.",
        "inputs": ["기온", "요일", "과거사용량"],
        "outputs": ["시간별 수요", "피크시각"],
        "url": "/api/pipelines/run?id=power-demand",
    },
]

# 외부 API 성격의 노드(시뮬레이터가 아닌 연계 서비스).
SERVICES: List[Dict[str, Any]] = [
    {
        "name": "디지털트윈 메타데이터 조회",
        "category": "연합트윈 연계",
        "api_id": "fedit.meta.dts",
        "description": "디지털트윈 상세 메타데이터를 조회한다.",
        "inputs": ["digitalTwinId"],
        "outputs": ["메타데이터", "simulations"],
        "bpmn_type": "bpmn:ServiceTask",
    },
    {
        "name": "시뮬레이션 메타데이터 조회",
        "category": "연합트윈 연계",
        "api_id": "fedit.meta.simulations",
        "description": "등록된 시뮬레이션 목록/상세를 조회한다.",
        "inputs": ["simulationId"],
        "outputs": ["simulationName", "입출력 정의"],
        "bpmn_type": "bpmn:ServiceTask",
    },
    {
        "name": "디지털트윈 검색",
        "category": "연합트윈 연계",
        "api_id": "fedit.search",
        "description": "키워드로 디지털트윈을 검색한다.",
        "inputs": ["검색어"],
        "outputs": ["트윈 목록"],
        "bpmn_type": "bpmn:ServiceTask",
    },
    {
        "name": "관측 데이터 수집",
        "category": "데이터",
        "api_id": "data.collect",
        "description": "센서·관측 데이터를 수집한다.",
        "inputs": ["센서ID", "기간"],
        "outputs": ["시계열 데이터"],
        "bpmn_type": "bpmn:ServiceTask",
    },
    {
        "name": "데이터 정제·전처리",
        "category": "데이터",
        "api_id": "data.preprocess",
        "description": "결측치 제거와 정규화를 수행한다.",
        "inputs": ["원본 데이터"],
        "outputs": ["정제 데이터"],
        "bpmn_type": "bpmn:ServiceTask",
    },
    {
        "name": "임계치 판정",
        "category": "분석",
        "api_id": "analysis.threshold",
        "description": "지표가 기준값을 넘는지 판정한다.",
        "inputs": ["지표값", "임계치"],
        "outputs": ["초과여부", "심각도"],
        "bpmn_type": "bpmn:Task",
    },
    {
        "name": "이상 탐지",
        "category": "분석",
        "api_id": "analysis.anomaly",
        "description": "시계열에서 이상 구간을 탐지한다.",
        "inputs": ["시계열 데이터"],
        "outputs": ["이상구간", "점수"],
        "bpmn_type": "bpmn:Task",
    },
    {
        "name": "SMS 알림 발송",
        "category": "알림",
        "api_id": "notify.sms",
        "description": "문자 메시지로 알림을 발송한다.",
        "inputs": ["수신번호", "메시지"],
        "outputs": ["발송상태"],
        "bpmn_type": "bpmn:SendTask",
    },
    {
        "name": "유관기관 통보",
        "category": "알림",
        "api_id": "notify.agency",
        "description": "소방·경찰 등 유관기관에 상황을 통보한다.",
        "inputs": ["기관코드", "상황정보"],
        "outputs": ["접수번호"],
        "bpmn_type": "bpmn:SendTask",
    },
    {
        "name": "디지털 사이니지 표출",
        "category": "알림",
        "api_id": "notify.signage",
        "description": "현장 전광판에 안내를 표출한다.",
        "inputs": ["표출문구", "대상지점"],
        "outputs": ["표출상태"],
        "bpmn_type": "bpmn:SendTask",
    },
    {
        "name": "결과 저장",
        "category": "데이터",
        "api_id": "data.store",
        "description": "처리 결과를 저장소에 적재한다.",
        "inputs": ["결과 데이터"],
        "outputs": ["저장경로"],
        "bpmn_type": "bpmn:ServiceTask",
    },
]


def simulation_entries() -> List[Dict[str, Any]]:
    """디지털 트윈 소스 형태로 정규화한 시뮬레이션 목록."""
    entries = []
    for index, item in enumerate(SIMULATIONS, start=1):
        entries.append({
            "id": index,
            "name": item["name"],
            "category": item["category"],
            "url": item["url"],
            "meta": {
                "twin": item["twin"],
                "twinId": item["twin_id"],
                "provider": item["provider"],
                "description": item["description"],
                "inputs": item["inputs"],
                "outputs": item["outputs"],
                "source": "catalog",
            },
        })
    return entries


def service_entries() -> List[Dict[str, Any]]:
    """외부 API 노드 카탈로그 형태로 정규화한 서비스 목록."""
    entries = []
    for index, item in enumerate(SERVICES, start=1):
        entries.append({
            "id": f"custom_{index}",
            "name": item["name"],
            "category": item["category"],
            "api_id": item["api_id"],
            "description": item["description"],
            "schema": {"inputs": item["inputs"], "outputs": item["outputs"]},
            "bpmn_type": item["bpmn_type"],
            "icon": {
                "bpmn:ServiceTask": "bpmn-icon-service-task",
                "bpmn:SendTask": "bpmn-icon-send-task",
                "bpmn:Task": "bpmn-icon-task",
            }.get(item["bpmn_type"], "bpmn-icon-task"),
        })
    return entries
