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
        # 포항 스마트시티(GENIX) 대기환경 시뮬레이션 — 실제 연계 규격 반영
        # POST /atmosphere/simulation/manual/form
        "name": "대기환경 확산 시뮬레이션",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "네트로(포항)",
        "description": "지정 좌표를 기준으로 향후 48시간 풍향 변화에 따른 오염물질 확산을 모사한다.",
        "inputs": ["sensorType", "temp", "quantity", "timeInterval",
                   "latitude", "longitude", "laterTime"],
        "outputs": ["airSimul.out", "wind.json", "다운로드 URL"],
        "url": "https://genix.pohang-eum.kr/service/atmosphere/simulation/manual/form",
        "method": "POST",
        "params": {
            "laterTime": {"type": "String", "required": True, "sample": "24",
                          "desc": "현재로부터 시뮬레이션 종료시간(24시간 단위)"},
            "sensorType": {"type": "String", "required": True, "sample": "SO2",
                           "desc": "오염원 종류(SO2/NO2/NOx/PM10/Hg/다이옥신)"},
            "temp": {"type": "String", "required": True, "sample": "100", "desc": "오염원 온도"},
            "quantity": {"type": "String", "required": True, "sample": "200", "desc": "오염원 농도"},
            "timeInterval": {"type": "String", "required": True, "sample": "10",
                             "desc": "시뮬레이션 시각화 발생시간"},
            "latitude": {"type": "String", "required": True, "sample": "35.983864", "desc": "위도"},
            "longitude": {"type": "String", "required": True, "sample": "129.558286", "desc": "경도"},
            "presetName": {"type": "String", "required": False, "sample": "간편모드1",
                           "desc": "간편모드명(값이 있으면 저장)"},
        },
    },
    {
        "name": "대기환경 시뮬레이션 목록 조회",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "네트로(포항)",
        "description": "저장된 대기환경 시뮬레이션 간편모드 목록을 조회한다.",
        "inputs": [],
        "outputs": ["presetName", "airFileName", "windFileName", "description"],
        "url": "https://genix.pohang-eum.kr/service/atmosphere/simulation/manual/presets",
        "method": "GET",
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
    # --- 시범구역 조성(도심형) 서비스 --------------------------------------
    # 서비스별 입출력 데이터 정의를 반영한 항목.
    {
        "name": "CCTV 취약지 분석",
        "twin": "도심안전 디지털 트윈",
        "twin_id": "KR-02-K10000-20240006",
        "category": "도심안전",
        "provider": "부산진구 시범구역",
        "description": "인구·건물·상가·학교·범죄 통계를 종합해 CCTV 취약지를 분석한다.",
        "inputs": ["격자별 인구(총/유소년/고령/생산가능)", "연속수치지형도-건물", "상가 업소",
                   "초중고 위치", "어린이집", "경찰서 위치", "보안등 위치",
                   "CCTV 설치 현황", "CCTV 작동 상태", "5대 범죄 발생 통계", "한전주 정보"],
        "outputs": ["취약지 분석 지수 10종", "사용자 지수 2종"],
        "url": "/api/pipelines/run?id=cctv-vulnerability",
    },
    {
        "name": "CCTV 설치 시뮬레이션",
        "twin": "도심안전 디지털 트윈",
        "twin_id": "KR-02-K10000-20240006",
        "category": "도심안전",
        "provider": "부산진구 시범구역",
        "description": "설치 지점과 속성값을 설정해 CCTV 배치 효과를 모사한다.",
        "inputs": ["설치 지점", "설정 속성값"],
        "outputs": ["설치 시뮬레이션 결과"],
        "url": "/api/pipelines/run?id=cctv-placement",
    },
    {
        "name": "산사태 취약지 통합 모니터링",
        "twin": "방재 디지털 트윈",
        "twin_id": "KR-02-K10000-20240004",
        "category": "방재",
        "provider": "부산진구 시범구역",
        "description": "산사태 IoT 센서와 기상 관측·예보, 산림청 정보를 통합 감시한다.",
        "inputs": ["산사태 IoT 센서", "기상청 관측·예보 강우", "산림청 산사태 정보"],
        "outputs": ["통합 모니터링 정보(15종)"],
        "url": "/api/pipelines/run?id=landslide-monitor",
    },
    {
        "name": "산사태 취약지 위험도 분석",
        "twin": "방재 디지털 트윈",
        "twin_id": "KR-02-K10000-20240004",
        "category": "방재",
        "provider": "부산진구 시범구역",
        "description": "실태 조사 판정표와 위험 지도, 급경사지 정보로 위험도를 산정한다.",
        "inputs": ["실태 조사 판정표", "산사태 위험 지도", "급경사지", "토지 특성", "사방댐"],
        "outputs": ["위험도 분석 정보(40종)"],
        "url": "/api/pipelines/run?id=landslide-risk",
    },
    {
        "name": "산사태 취약지 시뮬레이션",
        "twin": "방재 디지털 트윈",
        "twin_id": "KR-02-K10000-20240004",
        "category": "방재",
        "provider": "부산진구 시범구역",
        "description": "토사 재해 유동심·유속을 포함한 산사태 확산을 모사한다.",
        "inputs": ["위험도 분석 레이어", "강우 시나리오"],
        "outputs": ["유동심 레이어", "유속 레이어", "시뮬레이션 정보(11종)"],
        "url": "/api/pipelines/run?id=landslide-sim",
    },
    {
        "name": "재비산먼지 확산 시뮬레이션",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "부산진구 시범구역",
        "description": "기상·대기질 자료로 재비산먼지 확산을 계산하고 취약시설 영향을 매칭한다.",
        "inputs": ["요청 사용자 ID", "요청 시각", "기상 데이터", "대기질 데이터", "오염 물질 유형"],
        "outputs": ["전체 격자 통합 결과", "취약 시설별 계산 결과"],
        "url": "/api/pipelines/run?id=resuspended-dust",
    },
    {
        "name": "실시간 공기질 모니터링",
        "twin": "환경 디지털 트윈",
        "twin_id": "KR-02-K10000-20240001",
        "category": "환경",
        "provider": "부산진구 시범구역",
        "description": "버스 장착 센서로 이동 경로상의 공기질을 실시간 수집한다.",
        "inputs": ["버스 노선 좌표", "버스 정류장", "센서 ID"],
        "outputs": ["PM10", "PM2.5", "VOCs"],
        "url": "/api/pipelines/run?id=airquality-monitor",
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
        meta = {
            "twin": item["twin"],
            "twinId": item["twin_id"],
            "provider": item["provider"],
            "description": item["description"],
            "inputs": item["inputs"],
            "outputs": item["outputs"],
            "method": item.get("method", "POST"),
            "source": "catalog",
        }
        # 실제 연계 규격이 있는 항목은 요청 파라미터 정의도 함께 노출한다.
        if item.get("params"):
            meta["params"] = item["params"]
        entries.append({
            "id": index,
            "name": item["name"],
            "category": item["category"],
            "url": item["url"],
            "meta": meta,
        })
    return entries


def all_entries() -> List[Dict[str, Any]]:
    """시뮬레이션과 연계 서비스를 합친 목록(이름·분류·URL 기준)."""
    entries = [
        {
            "name": item["name"],
            "category": item["category"],
            "url": item["url"],
            "provider": item["provider"],
            "bpmn_type": "bpmn:ServiceTask",
            "twin_id": item["twin_id"],
        }
        for item in SIMULATIONS
    ]
    entries += [
        {
            "name": item["name"],
            "category": item["category"],
            "url": f"/api/pipelines/run?id={item['api_id']}",
            "provider": "",
            "bpmn_type": item["bpmn_type"],
            "twin_id": "",
        }
        for item in SERVICES
    ]
    return entries


def index_by_name() -> Dict[str, Dict[str, Any]]:
    """이름으로 카탈로그 항목을 찾기 위한 색인."""
    return {item["name"]: item for item in all_entries()}


def names() -> List[str]:
    """모델이 고를 수 있는 카탈로그 항목 이름 목록."""
    return [item["name"] for item in all_entries()]


def prompt_catalog(limit: int = 60) -> str:
    """시스템 프롬프트에 넣을 카탈로그 요약.

    모델이 임의로 이름을 지어내지 않고 실제 등록된 시뮬레이터·서비스를
    고르도록 분류별로 정리해 제공한다.
    """
    grouped: Dict[str, List[str]] = {}
    for item in all_entries()[:limit]:
        grouped.setdefault(item["category"], []).append(item["name"])
    lines = []
    for category, items in grouped.items():
        lines.append(f"- {category}: " + " / ".join(items))
    return "\n".join(lines)


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
