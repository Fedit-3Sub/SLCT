"""실연계되지 않은 카탈로그 노드의 모의 응답.

카탈로그 항목 대부분은 아직 실제 시스템과 연결되지 않아 실행 URL 이
`/api/pipelines/run?id=<식별자>` 로 되어 있다. 이 경로로 들어온 요청에는
항목에 정의된 출력 이름대로 값을 채워 돌려줘서, 로직 실행기가 다음 노드로
값을 넘기는 흐름을 끝까지 확인할 수 있게 한다.

같은 입력이면 같은 값이 나오도록 입력을 씨앗으로 쓴다. 응답에는 모의 값임을
알리는 `_mock: true` 를 붙인다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

from digitaltwins import catalog

MOCK_PATH = "/api/pipelines/run"

GRADES = ["좋음", "보통", "나쁨", "매우나쁨"]


def is_mock_url(url: str) -> bool:
    """카탈로그의 모의 실행 경로인지."""
    return urlsplit(url or "").path.rstrip("/") == MOCK_PATH


def mock_id(url: str) -> str:
    return (parse_qs(urlsplit(url or "").query).get("id") or [""])[0]


def _outputs_by_id() -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for item in catalog.SIMULATIONS:
        if is_mock_url(item["url"]):
            index[mock_id(item["url"])] = list(item["outputs"])
    for item in catalog.SERVICES:
        index[item["api_id"]] = list(item["outputs"])
    return index


def _value_for(name: str, seed: bytes) -> Any:
    digest = hashlib.sha256(seed + name.encode("utf-8")).digest()
    number = int.from_bytes(digest[:4], "big")
    if "등급" in name or "심각도" in name:
        return GRADES[number % len(GRADES)]
    if "여부" in name:
        return bool(number % 2)
    if "상태" in name:
        return "완료"
    if "번호" in name or name.endswith("ID") or name.endswith("id"):
        return f"MOCK-{number % 100000:05d}"
    if "경로" in name or "URL" in name:
        return f"/mock/{name}/{number % 1000}"
    # 이름에 맞는 현실적인 범위로 둔다. 범위를 벗어난 값(점유율 130% 등)은
    # 다음 노드의 계산을 왜곡해 흐름 확인을 어렵게 한다.
    low, high = _range_for(name)
    return round(low + (number % 10000) / 10000 * (high - low), 2)


RANGES = [
    (("PM2.5", "pm25", "PM25"), (5, 70)),
    (("PM10", "pm10", "미세먼지"), (10, 120)),
    (("점유율", "혼잡도", "율", "률", "지수", "점수"), (0, 100)),
    (("기온", "온도"), (-5, 35)),
    (("습도",), (20, 95)),
    (("시간", "소요"), (5, 120)),
]


def _range_for(name: str):
    for keywords, bounds in RANGES:
        if any(k in name for k in keywords):
            return bounds
    return (0, 150)


def outputs_for(sim_id: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """식별자에 정의된 출력 이름대로 모의 값을 만든다."""
    names = _outputs_by_id().get(sim_id)
    if names is None:
        names = ["result"]
    seed = (sim_id + json.dumps(inputs or {}, ensure_ascii=False, sort_keys=True, default=str)).encode("utf-8")
    result: Dict[str, Any] = {name: _value_for(name, seed) for name in names}
    result["_mock"] = True
    return result
