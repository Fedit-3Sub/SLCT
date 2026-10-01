"""연합트윈 Digital Brain 실데이터 어댑터.

Digital Brain 은 연합트윈(FDT)·연합객체(FDO)·시뮬레이션을 관리하고, 연합객체에
동기화된 센서 데이터를 시계열로 쌓는다. 응답은 NGSI-LD 형태로 깊게 중첩돼 있어
그대로는 로직 노드에서 쓰기 어렵다. 이 모듈은 그 데이터를 `co`, `temperature`
같은 평평한 이름으로 풀어 노드의 출력으로 바로 쓸 수 있게 한다.

환경변수
    FEDIT_BRAIN_URL      Digital Brain 주소 (기본 http://220.124.222.84:1213)
    FEDIT_BRAIN_TIMEOUT  요청 제한시간(초, 기본 6)

주요 경로 (인증 없음, 봉투 없는 JSON)
    GET  /fedit/v1/federated-twins
    GET  /fedit/v1/federated-twins/{fdt}/federated-digital-objects
    GET  /fedit/v1/federated-twins/{fdt}/federated-digital-objects/{fdo}/data?count=N
    GET  /fedit/v1/federated-twins/{fdt}/simulations
    POST /fedit/v1/federated-twins/{fdt}/simulations
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://220.124.222.84:1213"
CATALOG_TTL = 600          # 연합객체 목록·출력 이름 캐시(초)
MAX_OUTPUT_NAMES = 40      # 노드 출력으로 노출할 이름 수 상한


class BrainError(RuntimeError):
    """Digital Brain 에 접속할 수 없거나 응답이 올바르지 않을 때."""


def base_url() -> str:
    return os.environ.get("FEDIT_BRAIN_URL", DEFAULT_BASE_URL).rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("FEDIT_BRAIN_TIMEOUT", 6))
    except (TypeError, ValueError):
        return 6.0


def _request(method: str, path: str, **kwargs) -> Any:
    url = f"{base_url()}/fedit/v1{path}"
    try:
        resp = requests.request(method, url, timeout=_timeout(), **kwargs)
    except requests.RequestException as exc:
        raise BrainError(f"Digital Brain 에 접속하지 못했습니다: {exc.__class__.__name__}") from exc
    if resp.status_code >= 400:
        raise BrainError(f"Digital Brain 응답 오류 HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise BrainError("Digital Brain 응답이 JSON 이 아닙니다.") from exc


def _as_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("data", [])
    return [x for x in (data or []) if isinstance(x, dict)]


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------

def federated_twins() -> List[Dict[str, Any]]:
    return _as_list(_request("GET", "/federated-twins"))


def federated_objects(fdt: str) -> List[Dict[str, Any]]:
    return _as_list(_request("GET", f"/federated-twins/{fdt}/federated-digital-objects"))


def object_rows(fdt: str, fdo: str, count: int = 1) -> List[Dict[str, Any]]:
    count = max(1, min(int(count), 500))
    return _as_list(_request(
        "GET", f"/federated-twins/{fdt}/federated-digital-objects/{fdo}/data", params={"count": count},
    ))


def simulations(fdt: str) -> List[Dict[str, Any]]:
    return _as_list(_request("GET", f"/federated-twins/{fdt}/simulations"))


def register_simulation(fdt: str, body: Dict[str, Any]) -> Any:
    return _request("POST", f"/federated-twins/{fdt}/simulations", json=body)


# ---------------------------------------------------------------------------
# 평탄화
# ---------------------------------------------------------------------------

def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _summarize_measurements(items: List[Any]) -> Dict[str, Any]:
    """측정값 배열(날씨·교통 등)을 가장 최근 시각 기준 하나의 값 묶음으로 줄인다.

    같은 시각에 여러 지점 값이 있으면(도로 링크별 교통량 등) 숫자는 평균을 낸다.
    """
    rows = [x for x in items if isinstance(x, dict)]
    if not rows:
        return {}
    latest = max((str(r.get("date_time", "")) for r in rows), default="")
    current = [r for r in rows if str(r.get("date_time", "")) == latest] or rows[-1:]
    out: Dict[str, Any] = {}
    for key in current[-1]:
        values = [r.get(key) for r in current]
        numbers = [v for v in values if _is_number(v)]
        if numbers and len(numbers) == len(values) and not key.endswith("_id"):
            out[key] = round(sum(numbers) / len(numbers), 4)
        else:
            out[key] = values[-1]
    return out


def _walk(node: Any, prefix: str, out: Dict[str, Any], observed: List[str]) -> None:
    if isinstance(node, dict):
        # NGSI-LD Property / GeoProperty
        if "value" in node and ("type" in node or "observedAt" in node):
            if node.get("observedAt"):
                observed.append(str(node["observedAt"]))
            _walk(node["value"], prefix, out, observed)
            return
        if node.get("type") == "Point" and "coordinates" in node:
            out[prefix] = node["coordinates"]
            return
        for key, value in node.items():
            if key in ("id", "type", "@context"):
                continue
            _walk(value, f"{prefix}.{key}" if prefix else key, out, observed)
    elif isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node):
            for key, value in _summarize_measurements(node).items():
                out[f"{prefix}.{key}" if prefix else key] = value
        else:
            out[prefix] = node
    else:
        out[prefix] = node


def flatten_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """연합객체 데이터 한 행을 평평한 값 묶음으로 바꾼다.

    결과에는 디지털객체별 전체 이름(`KR-104111-0024.co`)과 짧은 이름(`co`)이 함께
    들어간다. 짧은 이름은 여러 디지털객체에 같은 속성이 있으면 숫자 평균,
    아니면 처음 나온 값이다. 측정값 배열 이름(`weatherMeasurement.`)도 짧은
    이름에서는 뺀다.
    """
    full: Dict[str, Any] = {}
    observed: List[str] = []
    _walk(row.get("data") or {}, "", full, observed)

    grouped: Dict[str, List[Any]] = {}
    for key, value in full.items():
        short = key.split(".")[-1]
        grouped.setdefault(short, []).append(value)

    result: Dict[str, Any] = {}
    for short, values in grouped.items():
        numbers = [v for v in values if _is_number(v)]
        is_identifier = short.endswith("_id") or short.endswith("Id") or short == "id"
        if len(values) > 1 and numbers and len(numbers) == len(values) and not is_identifier:
            result[short] = round(sum(numbers) / len(numbers), 4)
        else:
            result[short] = values[0]
    for key, value in full.items():
        if "." in key:
            result[key] = value

    result["rowtime"] = row.get("rowtime")
    if observed:
        result["observedAt"] = max(observed)
    return result


def latest(fdt: str, fdo: str) -> Dict[str, Any]:
    rows = object_rows(fdt, fdo, 1)
    if not rows:
        raise BrainError(f"연합객체 {fdo} 에 데이터가 없습니다.")
    return flatten_row(rows[0])


def series(fdt: str, fdo: str, prop: str, count: int = 24) -> Dict[str, Any]:
    """속성 하나의 최근 값 목록과 요약 통계."""
    rows = object_rows(fdt, fdo, count)
    points = []
    for row in rows:
        value = flatten_row(row).get(prop)
        if value is not None:
            points.append({"time": row.get("rowtime"), "value": value})
    numbers = [p["value"] for p in points if _is_number(p["value"])]
    return {
        "property": prop,
        "count": len(points),
        "values": points,
        "latest": points[0]["value"] if points else None,
        "min": min(numbers) if numbers else None,
        "max": max(numbers) if numbers else None,
        "avg": round(sum(numbers) / len(numbers), 4) if numbers else None,
    }


# ---------------------------------------------------------------------------
# 노드 카탈로그
# ---------------------------------------------------------------------------

_catalog_lock = threading.Lock()
_catalog_cache: Tuple[float, List[Dict[str, Any]]] = (0.0, [])


def _object_entry(fdt: Dict[str, Any], fdo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fdt_id = fdt.get("federated_digital_twin_id")
    fdo_id = fdo.get("federated_digital_object_id")
    if not fdt_id or not fdo_id:
        return None
    try:
        sample = latest(fdt_id, fdo_id)
    except BrainError:
        return None  # 데이터가 없는 연합객체는 노드로 내놓지 않는다.
    # 노드 출력으로는 측정값(숫자)만 내놓는다. 이름·설명 같은 메타데이터 문자열은
    # 응답에는 남지만 목록을 어지럽히므로 제외한다.
    names = [k for k, v in sample.items() if "." not in k and _is_number(v)]
    return {
        "fdt_id": fdt_id,
        "fdt_name": fdt.get("federated_digital_twin_name") or fdt_id,
        "fdo_id": fdo_id,
        "fdo_name": fdo.get("federated_digital_object_name") or fdo_id,
        "outputs": names[:MAX_OUTPUT_NAMES] + ["observedAt", "rowtime"],
        "rowtime": sample.get("rowtime"),
    }


def object_catalog(refresh: bool = False) -> List[Dict[str, Any]]:
    """데이터가 들어오는 연합객체 목록과 각 객체의 출력 이름. 접속 실패 시 빈 목록."""
    global _catalog_cache
    with _catalog_lock:
        stamp, cached = _catalog_cache
        if not refresh and cached and time.time() - stamp < CATALOG_TTL:
            return cached
        try:
            twins = federated_twins()
        except BrainError as exc:
            logger.info("Digital Brain 카탈로그를 가져오지 못했습니다: %s", exc)
            return cached
        pairs = []
        for fdt in twins:
            try:
                pairs += [(fdt, fdo) for fdo in federated_objects(fdt.get("federated_digital_twin_id", ""))]
            except BrainError:
                continue
        with ThreadPoolExecutor(max_workers=8) as pool:
            entries = [e for e in pool.map(lambda p: _object_entry(*p), pairs) if e]
        _catalog_cache = (time.time(), entries)
        return entries
