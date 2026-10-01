"""요구사항 → 실행 가능한 서비스 로직(spec) 생성.

LLM 이 BPMN 전체(노드·연결·이름)를 자유롭게 설계하게 하면 소형 모델은 단계를
빠뜨리고, 분기 조건을 만들지 않고, 이름을 틀린다. 그래서 역할을 나눈다.

    1. LLM 은 작은 양식(plan)만 채운다
       - 어떤 데이터·시뮬레이션을 쓸지(sources)      ← 등록된 이름 중에서만 고름
       - 어떤 값을 어떤 기준으로 판단할지(check)
       - 조건을 만족하면 할 일(alert_actions)         ← 등록된 이름 중에서만 고름
       - 목록에 없는 추가 작업(extra_steps), 마지막에 항상 할 일(final_actions)
    2. 코드가 plan 을 고친다(normalize_plan)
       모델이 비우거나 틀린 칸을 요구사항의 핵심어와 기본값으로 채운다.
    3. 코드가 plan 으로 실행 가능한 spec 을 조립한다(build_spec)
       병렬 수집, 조건 분기(조건식 포함), 동작의 입력 매핑, 결과 정의까지 넣는다.

외부 LLM·내장 LLM·규칙 기반 모두 같은 2~3단계를 거치므로, 어느 엔진이든
결과는 바로 실행된다. 규칙 기반은 빈 plan 을 넘겨 2단계가 전부 채우게 한다.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

OPS = [">", ">=", "<", "<=", "=="]
MAX_SOURCES = 3
LIVE_DAYS = 45          # 이 기간 안에 데이터가 들어온 연합객체를 '실데이터' 소스로 쓴다
PROMPT_OUTPUTS = 10     # 프롬프트에 보여줄 소스별 출력 이름 수

# 프롬프트·출력 순서에서 앞에 둘 측정값(사람이 자주 묻는 값)
PRIORITY_OUTPUTS = (
    "pm10", "pm25", "temp", "temperature", "humi", "humidity", "winsp", "wind_speed",
    "speed", "tfvl", "precipitation_percent", "co", "o3", "no2", "so2", "voc",
    "waterTemperature", "salinity", "airTemperature", "windSpeed",
)

# 요구사항 핵심어 → 판단할 값 후보(앞쪽 우선)
METRIC_HINTS: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = [
    (("초미세",), ("pm25", "PM2.5", "PM25")),
    (("미세먼지", "대기질", "공기질", "먼지"), ("pm10", "PM10")),
    (("폭염", "기온", "온도", "더위", "추위"), ("temp", "temperature", "기온", "airTemperature")),
    (("습도",), ("humi", "humidity", "습도")),
    (("풍속", "바람", "강풍"), ("winsp", "wind_speed", "windSpeed", "풍속")),
    (("수온",), ("waterTemperature", "temper")),
    (("염분",), ("salinity",)),
    (("교통량",), ("tfvl", "교통량")),
    (("속도", "정체"), ("speed", "도로평균속도")),
    (("쾌적",), ("쾌적지수",)),
    (("혼잡",), ("혼잡도", "예측점유율", "혼잡등급")),
    (("주차",), ("예측점유율", "혼잡등급")),
    (("침수",), ("침수심",)),
    (("이상", "고장", "오류"), ("점수", "이상구간")),
    (("강우", "비", "강수"), ("precipitation_percent", "강우량")),
]

# 판단 값별 기본 기준값과 비교 방향
DEFAULT_THRESHOLDS: List[Tuple[Tuple[str, ...], str, float]] = [
    (("pm25", "PM2.5", "PM25"), ">", 35),
    (("pm10", "PM10"), ">", 80),
    (("temp", "temperature", "기온", "airTemperature"), ">", 33),
    (("humi", "humidity", "습도"), ">", 80),
    (("winsp", "wind_speed", "windSpeed", "풍속"), ">", 14),
    (("speed", "도로평균속도"), "<", 20),
    (("쾌적지수",), "<", 50),
    (("혼잡도", "예측점유율"), ">", 70),
    (("점수",), ">", 70),
    (("precipitation_percent",), ">", 60),
]

ACTION_HINTS: List[Tuple[Tuple[str, ...], str]] = [
    (("문자", "sms", "메시지"), "SMS 알림 발송"),
    (("기관", "통보", "신고", "보고", "지자체", "소방"), "유관기관 통보"),
    (("사이니지", "전광판", "표출", "안내판", "게시"), "디지털 사이니지 표출"),
]
# 어떤 수단인지 말하지 않은 '알림·경보' 는 다른 동작이 하나도 없을 때만 문자 발송으로 본다.
WEAK_NOTIFY = ("알림", "알려", "경보", "통지", "알리")
STORE_HINTS = ("저장", "기록", "이력", "적재", "보관", "로그")
CONDITION_HINTS = ("하면", "되면", "이면", "으면", "나쁘", "높으", "낮으", "넘으", "초과", "이상", "미만",
                   "이하", "감지", "발생", "경우", "때")

# 요구사항 핵심어 → 데이터 소스 이름에 들어 있을 단어
SOURCE_HINTS: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = [
    (("미세먼지", "대기", "공기", "포항", "환경"), ("포항 환경",)),
    (("해양", "바다", "수온", "염분", "양식"), ("해양 기상", "해양 대기")),
    (("관광객", "방문객", "인파", "밀집", "관광지 혼잡", "관광지가 혼잡"), ("관광 디지털 트윈 시뮬레이션",)),
    (("쾌적",), ("관광지 쾌적지수",)),
    (("날씨", "기상", "제주"), ("관광지 교통·기상",)),
    (("주차",), ("주차장 혼잡도",)),
    (("도로", "교통", "정체", "사고"), ("도로혼잡도",)),
    (("산사태", "급경사"), ("산사태 취약지 통합",)),
    (("침수", "홍수", "강우"), ("침수",)),
    (("전력", "에너지"), ("전력",)),
    (("센서", "관측", "수집"), ("관측 데이터 수집",)),
    (("이상", "고장"), ("이상 탐지",)),
]


# ---------------------------------------------------------------------------
# 등록 항목(데이터 소스·동작)
# ---------------------------------------------------------------------------

ENV_OUTPUTS = {"pm10", "pm25", "temp", "temperature", "humi", "humidity", "speed", "tfvl",
               "waterTemperature", "salinity", "winsp", "wind_speed", "co", "o3"}
READABLE_NAMES = [
    ("연합 모델 (2개 통합) MARINE_ATMOSPHERE", "해양 대기(영일만)"),
    ("연합 모델 (2개 통합) MARINE_WEATHER", "해양 기상(영일만)"),
    ("MARINE_ATMOSPHERE", "해양 대기"),
    ("MARINE_WEATHER", "해양 기상"),
]


def _is_fresh(rowtime: Optional[str]) -> bool:
    if not rowtime:
        return False
    try:
        stamp = datetime.fromisoformat(str(rowtime).replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - stamp < timedelta(days=LIVE_DAYS)


def _ordered(outputs: List[str]) -> List[str]:
    rank = {name: i for i, name in enumerate(PRIORITY_OUTPUTS)}
    return sorted(outputs, key=lambda n: rank.get(n, len(rank)))


def _fedit_sources() -> List[Dict[str, Any]]:
    """연합트윈 Digital Brain 의 연합객체를 데이터 소스로. 접속할 수 없으면 빈 목록."""
    try:
        from urllib.parse import urlencode

        from digitaltwins import brain
        entries = brain.object_catalog()
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    jeju_added = False
    for item in entries:
        name = item["fdo_name"]
        if re.search(r"test|control|^KR\d", name, re.I):
            continue
        # 환경·교통처럼 로직에서 판단할 측정값이 있는 연합객체만 쓴다(사료·금속 시험 객체 제외).
        if not set(item["outputs"]) & ENV_OUTPUTS:
            continue
        for raw, readable in READABLE_NAMES:
            name = name.replace(raw, readable)
        name = re.sub(r"\s+", " ", name).strip()
        outputs = [o for o in item["outputs"] if o not in ("rowtime",)]
        query = urlencode({"fdt": item["fdt_id"], "fdo": item["fdo_id"]})
        base = {
            "url": f"/api/fedit/objects/latest?{query}",
            "method": "GET",
            "outputs": _ordered(outputs),
            "inputs": [],
            "kind": "fedit",
        }
        if _is_fresh(item.get("rowtime")):
            out.append({**base, "name": f"{name} 실데이터"[:60],
                        "description": f"연합트윈 {item['fdt_name']} 의 실시간 데이터"})
        elif item["fdt_name"].upper().startswith("JEJU") and not jeju_added and "성산" in name:
            # 제주 관광지는 갱신이 멈춘 상태지만 관광 시나리오의 실데이터로 하나를 둔다.
            jeju_added = True
            out.append({**base, "name": "제주 관광지 교통·기상 실데이터",
                        "description": f"연합트윈 제주 관광지({name}) 교통·기상 데이터"})
    return out


def _catalog_sources() -> List[Dict[str, Any]]:
    from digitaltwins import catalog
    from pipelines import mock

    out = []
    for item in catalog.SIMULATIONS:
        if not mock.is_mock_url(item["url"]):
            continue  # 실제 시스템을 바로 실행하는 항목(GENIX 등)은 자동 생성에서 제외
        out.append({"name": item["name"], "url": item["url"], "method": item.get("method", "POST"),
                    "outputs": list(item["outputs"]), "inputs": list(item["inputs"]), "kind": "catalog",
                    "description": item["description"]})
    for item in catalog.SERVICES:
        if item["category"] in ("데이터", "분석") or item["api_id"].startswith(("data.collect", "data.preprocess", "analysis.anomaly")):
            out.append({"name": item["name"], "url": f"{mock.MOCK_PATH}?id={item['api_id']}", "method": "POST",
                        "outputs": list(item["outputs"]), "inputs": list(item["inputs"]), "kind": "catalog",
                        "description": item["description"]})
    return out


ACTIONS: Dict[str, Dict[str, Any]] = {
    "SMS 알림 발송": {"api_id": "notify.sms", "type": "sendTask",
                   "inputs": [("수신번호", "value", "담당자"), ("메시지", "message", "")], "outputs": ["발송상태"]},
    "유관기관 통보": {"api_id": "notify.agency", "type": "sendTask",
                  "inputs": [("기관코드", "value", "관할기관"), ("상황정보", "message", "")], "outputs": ["접수번호"]},
    "디지털 사이니지 표출": {"api_id": "notify.signage", "type": "serviceTask",
                     "inputs": [("표출문구", "message", ""), ("대상지점", "value", "현장")], "outputs": ["표출상태"]},
    "결과 저장": {"api_id": "data.store", "type": "serviceTask",
              "inputs": [("결과 데이터", "result", "")], "outputs": ["저장경로"]},
}


def registry() -> Dict[str, Dict[str, Any]]:
    """데이터 소스 이름 → 항목."""
    items = _fedit_sources() + _catalog_sources()
    return {item["name"]: item for item in items}


# ---------------------------------------------------------------------------
# LLM 양식
# ---------------------------------------------------------------------------

def plan_schema(source_names: List[str]) -> Dict[str, Any]:
    """구조화 출력용 JSON 스키마. 이름은 등록 목록(enum) 안에서만 고르게 한다."""
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string", "enum": source_names}, "maxItems": MAX_SOURCES},
            "check": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "op": {"type": "string", "enum": OPS},
                    "threshold": {"type": "number"},
                    "label": {"type": "string"},
                },
                "required": ["metric", "op", "threshold", "label"],
            },
            "alert_actions": {"type": "array", "items": {"type": "string", "enum": list(ACTIONS)}},
            "extra_steps": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "final_actions": {"type": "array", "items": {"type": "string", "enum": list(ACTIONS)}},
        },
        "required": ["title", "sources", "check", "alert_actions", "extra_steps", "final_actions"],
    }


EXAMPLE = {
    "title": "포항 미세먼지 경보",
    "sources": ["포항 환경 통합 연합 객체 실데이터"],
    "check": {"metric": "pm10", "op": ">", "threshold": 80, "label": "미세먼지 나쁨"},
    "alert_actions": ["SMS 알림 발송"],
    "extra_steps": [],
    "final_actions": ["결과 저장"],
}


def system_prompt(sources: Dict[str, Dict[str, Any]]) -> str:
    lines = [
        "당신은 연합 디지털트윈 서비스 로직 설계 도우미입니다. 요구사항을 읽고 JSON 양식만 채우세요.",
        "- title: 로직 이름(한국어, 짧게)",
        "- sources: 필요한 데이터·시뮬레이션을 [데이터 소스]에서 1~3개, 이름을 그대로 고릅니다.",
        "- check: 요구사항에 '~하면', '나쁘면', '초과', '이상' 같은 조건이 있으면 판단할 값(metric: 고른 소스의 출력 이름),"
        " 비교(op), 기준값(threshold, 숫자), 짧은 설명(label). 조건이 없으면 metric 을 빈 문자열로 둡니다.",
        "- alert_actions: 조건을 만족할 때 할 일을 [동작]에서 고릅니다.",
        "- extra_steps: [동작]에 없는 추가 작업 이름(예: 대피 경로 안내). 없으면 빈 배열.",
        "- final_actions: 조건과 상관없이 마지막에 할 일(예: 결과 저장).",
        "",
        "[데이터 소스] 이름: 출력 이름들",
    ]
    for name, item in sources.items():
        lines.append(f"- {name}: {', '.join(item['outputs'][:PROMPT_OUTPUTS])}")
    lines += ["", "[동작] " + " / ".join(ACTIONS), "",
              '예) 요구사항: "포항 미세먼지가 나쁘면 문자로 알리고 기록해줘"',
              json.dumps(EXAMPLE, ensure_ascii=False)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 보정
# ---------------------------------------------------------------------------

def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _match_output(metric: str, outputs: List[str]) -> str:
    if not metric:
        return ""
    if metric in outputs:
        return metric
    lowered = {o.lower(): o for o in outputs}
    if metric.lower() in lowered:
        return lowered[metric.lower()]
    # 부분 일치는 '찾는 이름이 출력 이름 안에 들어 있는' 방향만 본다. 반대 방향을 허용하면
    # waterTemperature 를 찾다가 temp(기온)가 걸리는 식의 오답이 난다.
    for output in outputs:
        if len(metric) >= 3 and metric.lower() in output.lower():
            return output
    return ""


CONDITION_MARK = re.compile(r"(하면|되면|이면|으면|나쁘면|높으면|낮으면|넘으면|초과하면|이상이면|감지하면|발생하면)")
LABELS: List[Tuple[Tuple[str, ...], str]] = [
    (("pm25", "PM2.5", "PM25"), "초미세먼지 나쁨"),
    (("pm10", "PM10"), "미세먼지 나쁨"),
    (("temp", "temperature", "기온", "airTemperature"), "고온"),
    (("humi", "humidity", "습도"), "고습"),
    (("winsp", "wind_speed", "windSpeed", "풍속"), "강풍"),
    (("speed", "도로평균속도"), "도로 정체"),
    (("쾌적지수",), "쾌적도 낮음"),
    (("혼잡도", "예측점유율"), "혼잡"),
    (("점수",), "이상 감지"),
    (("precipitation_percent",), "강수 예상"),
]


NON_METRIC = ("observedAt", "rowtime", "date_time", "location", "link_id", "measure_position_id")
NON_NUMERIC_WORDS = ("등급", "상태", "여부", "정보", "경로", "목록", "레이어", "데이터", "결과")
LOW_WORDS = ("미만", "이하", "낮으면", "낮아지면", "떨어지면", "아래로", "부족")
HIGH_WORDS = ("초과", "이상이면", "넘으면", "넘어가면", "높으면", "높아지면", "나쁘면", "많으면", "올라가면")


def _condition_clause(text: str) -> str:
    marks = list(CONDITION_MARK.finditer(text))
    if not marks:
        return text
    return text[max(0, marks[-1].start() - 16):marks[-1].end() + 4]


def _direction_from_text(text: str) -> str:
    clause = _condition_clause(text)
    if any(w in clause for w in LOW_WORDS):
        return "<"
    if any(w in clause for w in HIGH_WORDS):
        return ">"
    return ""


def _number_from_text(text: str) -> Optional[float]:
    """조건 표현 근처의 숫자(25도, 80㎍, 70%)."""
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:도|℃|㎍|ug|μg|%|퍼센트|m/s|km|이상|이하|초과|미만)?", _condition_clause(text))
    return float(match.group(1)) if match else None


def _metric_from_text(text: str, outputs: List[str]) -> str:
    # 조건 표현 바로 앞(예: "혼잡하면" 의 '혼잡')을 먼저 본다. 문장에 여러 값이 나와도
    # 실제로 판단하려는 값을 고르기 위함이다.
    marks = list(CONDITION_MARK.finditer(text))
    if marks:
        clause = text[max(0, marks[-1].start() - 12):marks[-1].start()]
        for keywords, candidates in METRIC_HINTS:
            if any(k in clause for k in keywords):
                for candidate in candidates:
                    found = _match_output(candidate, outputs)
                    if found:
                        return found
    for keywords, candidates in METRIC_HINTS:
        if any(k in text for k in keywords):
            for candidate in candidates:
                found = _match_output(candidate, outputs)
                if found:
                    return found
    return ""


def _default_threshold(metric: str) -> Tuple[str, float]:
    for names, op, value in DEFAULT_THRESHOLDS:
        if metric in names:
            return op, value
    return ">", 0


def _sources_from_text(text: str, sources: Dict[str, Dict[str, Any]]) -> List[str]:
    picked: List[str] = []
    for keywords, needles in SOURCE_HINTS:
        if any(k in text for k in keywords):
            for needle in needles:
                for name in sources:
                    if needle.lower() in name.lower() and name not in picked:
                        picked.append(name)
                        break
                else:
                    continue
                break
        if len(picked) >= MAX_SOURCES:
            break
    return picked


def _extra_from_text(text: str) -> List[str]:
    steps = []
    for match in re.finditer(r"([가-힣]+(?:\s[가-힣]+)?)\s?(?:를|을)?\s?안내", text):
        phrase = re.sub(r"(를|을|하고|하며|및)$", "", match.group(1)).strip()
        if phrase and phrase not in ("경로",):
            steps.append(f"{phrase} 안내")
    return steps[:2]


def normalize_plan(plan: Optional[Dict[str, Any]], prompt: str,
                   sources: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """모델 출력(또는 빈 plan)을 실행 가능한 plan 으로 고친다."""
    plan = plan if isinstance(plan, dict) else {}
    sources = sources if sources is not None else registry()
    text = (prompt or "").strip()
    lowered = text.lower()

    chosen = [s for s in _as_list(plan.get("sources")) if s in sources]
    chosen = list(dict.fromkeys(chosen))[:MAX_SOURCES]
    hinted = _sources_from_text(text, sources)
    if hinted:
        # 요구사항이 데이터를 직접 가리키면 그것만 쓴다. 소형 모델은 무관한 소스를
        # 덧붙이는 일이 잦다(해양 수온인데 금속 객체·제주 관광 데이터 등).
        # 모델이 고른 소스는 요구사항에서 단서를 찾지 못했을 때만 쓴다.
        chosen = hinted
    if not chosen and sources:
        fallback = "관측 데이터 수집" if "관측 데이터 수집" in sources else next(iter(sources))
        chosen = [fallback]
    outputs = [o for name in chosen for o in sources[name]["outputs"]]

    check_in = plan.get("check") if isinstance(plan.get("check"), dict) else {}
    wants_condition = any(k in text for k in CONDITION_HINTS)
    numeric = [o for o in outputs if o not in NON_METRIC and not any(w in o for w in NON_NUMERIC_WORDS)]
    if wants_condition and not numeric and "이상 탐지" in sources and "이상 탐지" not in chosen:
        # 판단할 수치가 없는 소스뿐이면(모니터링 정보 등) 이상 탐지 점수로 판단한다.
        chosen = chosen[:MAX_SOURCES - 1] + ["이상 탐지"]
        outputs = [o for name in chosen for o in sources[name]["outputs"]]
        numeric = [o for o in outputs if o not in NON_METRIC and not any(w in o for w in NON_NUMERIC_WORDS)]

    metric = ""
    if wants_condition:
        # 문장이 판단할 값을 분명히 말하면(혼잡하면, 수온이 … 넘으면) 그것을 모델 답보다 우선한다.
        metric = _metric_from_text(text, numeric)
        if not metric:
            model_metric = str(check_in.get("metric") or "").split(",")[0].strip()
            metric = _match_output(model_metric, numeric)
        if not metric:
            metric = numeric[0] if numeric else ""
    # 요구사항에 조건이 없으면 모델이 지어낸 조건은 버린다.

    check: Optional[Dict[str, Any]] = None
    if metric:
        default_op, default_value = _default_threshold(metric)
        model_op = check_in.get("op") if check_in.get("op") in OPS else ">"
        # 비교 방향: 문장 표현(넘으면/미만) > 값의 기본 방향(쾌적지수는 낮을수록 나쁨) > 모델 답
        op = _direction_from_text(text) or (default_op if default_value else model_op)
        threshold = _number_from_text(text)
        if threshold is None:
            try:
                threshold = float(check_in.get("threshold"))
            except (TypeError, ValueError):
                threshold = None
        if threshold is None or (threshold == 0 and default_value):
            threshold = default_value
        if float(threshold).is_integer():
            threshold = int(threshold)
        default_label = next((label for names, label in LABELS if metric in names), f"{metric} {op} {threshold}")
        label = str(check_in.get("label") or "").strip()[:30] or default_label
        check = {"metric": metric, "op": op, "threshold": threshold, "label": label}

    alert = [a for a in _as_list(plan.get("alert_actions")) if a in ACTIONS]
    final = [a for a in _as_list(plan.get("final_actions")) if a in ACTIONS]
    if not check:
        # 조건이 없으면 '조건 충족 시 동작'은 의미가 없다. 요구사항에 나온 동작만 아래에서 다시 넣는다.
        alert = []
        final = [a for a in final if a == "결과 저장" and any(k in text for k in STORE_HINTS)]
    for keywords, action in ACTION_HINTS:
        if any(k in lowered for k in keywords) and action not in alert and action not in final:
            (alert if check else final).append(action)
    if not [a for a in alert + final if a != "결과 저장"] and any(k in text for k in WEAK_NOTIFY):
        (alert if check else final).append("SMS 알림 발송")
    if any(k in text for k in STORE_HINTS) and "결과 저장" not in final:
        final.append("결과 저장")
    alert = [a for a in dict.fromkeys(alert) if a != "결과 저장" or not check]
    final = [a for a in dict.fromkeys(final) if a not in alert]
    if check and not alert:
        alert = ["SMS 알림 발송"]

    extra = [re.sub(r"\s+", " ", str(s)).strip()[:30] for s in _as_list(plan.get("extra_steps"))]
    extra = [s for s in extra if s and s not in ACTIONS and s not in sources]
    for step in _extra_from_text(text):
        if not any(step.split()[0] in e for e in extra):
            extra.append(step)
    extra = list(dict.fromkeys(extra))[:3]

    title = re.sub(r"\s+", " ", str(plan.get("title") or "")).strip()[:40]
    # 소형 모델은 한글 음절을 깨뜨리는 일이 있다(쾌적 → 쉉적). 요구사항에 없는 음절이
    # 들어 있으면 제목을 버리고 아래 기본값을 쓴다.
    allowed = set(text) | set("경보대응로직및처리계산예측알림관리모니터링서비스판단발송조회분석")
    if any("가" <= ch <= "힣" and ch not in allowed for ch in title):
        title = ""
    if not title:
        title = (check["label"] + " 대응") if check else (text[:20] or "서비스 로직")
    return {"title": title, "sources": chosen, "check": check,
            "alert_actions": alert, "extra_steps": extra, "final_actions": final}


# ---------------------------------------------------------------------------
# 조립
# ---------------------------------------------------------------------------

def _ref(name: str) -> str:
    """식에서 쓸 이름. 파이썬 식별자가 아니면 var("이름")."""
    return name if name.isidentifier() else f'var("{name}")'


def _has_dependency(names: List[str], sources: Dict[str, Dict[str, Any]]) -> bool:
    produced = {o for n in names for o in sources[n]["outputs"]}
    return any(i in produced for n in names for i in sources[n].get("inputs", []))


def _dependency_order(names: List[str], sources: Dict[str, Dict[str, Any]]) -> List[str]:
    """다른 소스의 출력을 입력으로 쓰는 소스를 뒤로 보낸다."""
    remaining, ordered = list(names), []
    while remaining:
        produced_by_rest = {o for n in remaining for o in sources[n]["outputs"]}
        ready = [n for n in remaining
                 if not any(i in produced_by_rest - set(sources[n]["outputs"]) for i in sources[n].get("inputs", []))]
        pick = ready[0] if ready else remaining[0]
        ordered.append(pick)
        remaining.remove(pick)
    return ordered


def build_spec(plan: Dict[str, Any], sources: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """plan → 실행 설정이 들어간 spec([bpmn_spec] 이 XML 로 만든다)."""
    from pipelines import mock

    sources = sources if sources is not None else registry()
    nodes: List[Dict[str, Any]] = []
    flows: List[Dict[str, Any]] = []
    counter = {"n": 0}

    def node(kind: str, name: str, **extra) -> str:
        counter["n"] += 1
        node_id = f"Node_{counter['n']}"
        nodes.append({"id": node_id, "type": kind, "name": name, **extra})
        return node_id

    def link(src: str, dst: str, name: str = "", condition: str = "") -> None:
        flows.append({"from": src, "to": dst, "name": name, "condition": condition})

    check = plan.get("check")
    title = plan["title"]
    metric_expr = _ref(check["metric"]) if check else ""
    condition = f"{metric_expr} {check['op']} {check['threshold']}" if check else ""
    message = (f"'[{title}] {check['label']} ({check['metric']}=' + str({metric_expr}) + ')'"
               if check else f"'[{title}] 처리 결과 알림'")

    first_source = sources.get(plan["sources"][0], {}) if plan["sources"] else {}
    key_outputs = [o for o in first_source.get("outputs", []) if o not in ("observedAt", "rowtime")][:3]
    if check and check["metric"] not in key_outputs:
        key_outputs = [check["metric"]] + key_outputs[:2]
    result_items = [(o, _ref(o)) for o in key_outputs]
    if check:
        result_items.append(("경보", condition))
    result_dict = "{" + ", ".join(f"'{k}': {v}" for k, v in result_items) + "}"

    def action_node(action: str) -> str:
        spec = ACTIONS[action]
        inputs = []
        for name, kind, value in spec["inputs"]:
            if kind == "value":
                inputs.append({"name": name, "value": value})
            elif kind == "message":
                inputs.append({"name": name, "source": message})
            elif kind == "result":
                inputs.append({"name": name, "source": result_dict})
        return node(spec["type"], action, url=f"{mock.MOCK_PATH}?id={spec['api_id']}", method="POST",
                    inputs=inputs, outputs=[{"name": o} for o in spec["outputs"]])

    start = node("startEvent", "시작")

    # 1) 데이터 수집. 서로 값을 주고받지 않으면 병렬, 한 소스가 다른 소스의 출력을
    #    입력으로 쓰면(혼잡도 → 쾌적지수) 만드는 쪽을 앞에 두고 직렬로 잇는다.
    ordered = _dependency_order(plan["sources"], sources)
    dependent = ordered != plan["sources"] or _has_dependency(plan["sources"], sources)
    source_ids = []
    for name in ordered:
        item = sources[name]
        source_ids.append(node(
            "serviceTask", name, url=item["url"], method=item.get("method", ""),
            inputs=[{"name": i} for i in item.get("inputs", [])],
            outputs=[{"name": o} for o in item["outputs"]],
            doc=item.get("description", ""),
        ))
    if len(source_ids) > 1 and dependent:
        link(start, source_ids[0])
        for a, b in zip(source_ids, source_ids[1:]):
            link(a, b)
        tail = source_ids[-1]
    elif len(source_ids) > 1:
        fork, join = node("parallelGateway", "동시 수집"), None
        link(start, fork)
        for sid in source_ids:
            link(fork, sid)
        join = node("parallelGateway", "수집 완료")
        for sid in source_ids:
            link(sid, join)
        tail = join
    elif source_ids:
        link(start, source_ids[0])
        tail = source_ids[0]
    else:
        tail = start

    # 2) 마지막 동작과 종료(결과 반환)
    end_inputs = [{"name": k, "source": v} for k, v in result_items]
    end = node("endEvent", "결과 반환", inputs=end_inputs)
    finals = [action_node(a) for a in plan["final_actions"]]

    def chain(ids: List[str], last: str) -> str:
        """ids 를 직렬로 잇고 마지막을 last 에 연결. 첫 노드(없으면 last)를 돌려준다."""
        for a, b in zip(ids, ids[1:]):
            link(a, b)
        if ids:
            link(ids[-1], last)
            return ids[0]
        return last

    after = chain(finals, end)

    # 3) 조건 분기
    alerts = [action_node(a) for a in plan["alert_actions"]] + [
        node("task", step, doc="자동 생성된 추가 작업(실행 URL 을 연결하면 호출된다)") for step in plan["extra_steps"]
    ]
    if check:
        gateway = node("exclusiveGateway", f"{check['label']}?", default_to=after)
        link(tail, gateway)
        first_alert = chain(alerts, after)
        link(gateway, first_alert, name="예", condition=condition)
        link(gateway, after, name="아니오")
    else:
        link(tail, chain(alerts, after))

    return {"name": title, "nodes": nodes, "flows": flows}


def describe(plan: Dict[str, Any]) -> str:
    """사용자에게 보여줄 한 줄 요약."""
    parts = [f"데이터: {', '.join(plan['sources']) or '없음'}"]
    if plan.get("check"):
        c = plan["check"]
        parts.append(f"조건: {c['metric']} {c['op']} {c['threshold']} ({c['label']})")
    if plan["alert_actions"] or plan["extra_steps"]:
        parts.append(f"조건 충족 시: {', '.join(plan['alert_actions'] + plan['extra_steps'])}")
    if plan["final_actions"]:
        parts.append(f"마지막: {', '.join(plan['final_actions'])}")
    return " · ".join(parts)
