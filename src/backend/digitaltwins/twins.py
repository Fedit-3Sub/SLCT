"""트윈 노드: 연합트윈 프레임워크에 실제로 등록된 트윈을 로직 노드로 쓰기 위한 어댑터.

노드는 URL 이 아니라 '트윈'이다. 노드마다 그 트윈의 메타정보(이름·소유 기관·
설명·키워드)와 속성 목록(이름·타입·지금 값)을 보여주고, 사용자는 로직에서 쓸
속성을 골라 출력으로 삼는다. 모든 정보는 프레임워크 API 에서 조회한 것만 쓴다.

트윈 참조(ref) 형식
    do:{디지털트윈 id}:{디지털객체 id}     단일 트윈의 디지털객체 (Digital Connector :1219)
    fdo:{연합트윈 id}:{연합객체 id}        연합 객체 (Digital Brain :1213)

환경변수
    FEDIT_CONNECTOR_URL  Digital Connector 주소 (기본 http://220.124.222.84:1219)
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from . import brain

logger = logging.getLogger(__name__)

DEFAULT_CONNECTOR_URL = "http://220.124.222.84:1219"
CATALOG_TTL = 600
DEFAULT_OUTPUTS = 8          # 노드를 처음 놓을 때 출력으로 고르는 속성 수
STALE_DAYS = 30


class TwinError(RuntimeError):
    """트윈을 찾을 수 없거나 프레임워크에 접속할 수 없을 때."""


def connector_url() -> str:
    return os.environ.get("FEDIT_CONNECTOR_URL", DEFAULT_CONNECTOR_URL).rstrip("/")


def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        resp = requests.get(url, params=params or {}, timeout=8)
    except requests.RequestException as exc:
        raise TwinError(f"연합트윈 프레임워크에 접속하지 못했습니다: {exc.__class__.__name__}") from exc
    if resp.status_code >= 400:
        raise TwinError(f"연합트윈 프레임워크 응답 오류 HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise TwinError("연합트윈 프레임워크 응답이 JSON 이 아닙니다.") from exc
    if isinstance(data, dict) and data.get("code") and data.get("msg") and "data" not in data:
        raise TwinError(f"연합트윈 프레임워크: {data.get('msg')}")
    return data


def _rows(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("data", [])
    return [x for x in (data or []) if isinstance(x, dict)]


# ---------------------------------------------------------------------------
# Digital Connector (단일 트윈)
# ---------------------------------------------------------------------------

def digital_twins() -> List[Dict[str, Any]]:
    return _rows(_get(f"{connector_url()}/fedit/v1/digital-twins"))


def digital_objects(dt: str) -> List[Dict[str, Any]]:
    return _rows(_get(f"{connector_url()}/fedit/v1/digital-twins/{dt}/digital-objects"))


def digital_object_rows(dt: str, do: str, count: int = 1) -> List[Dict[str, Any]]:
    return _rows(_get(f"{connector_url()}/fedit/v1/digital-twins/{dt}/digital-objects/{do}/data",
                      {"count": max(1, min(int(count), 200))}))


# ---------------------------------------------------------------------------
# 값 정리
# ---------------------------------------------------------------------------

_NUMBER = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")
# 사람이 흔히 판단에 쓰는 측정값(처음 출력으로 고를 때 앞에 둔다)
KEY_MEASURES = ("pm10", "pm25", "temp", "airTemperature", "AIR_TEMPERATURE", "temperature", "humi", "humidity",
                "HUMIDITY", "winsp", "windSpeed", "WIND_SPEED", "wind_speed", "temper", "waterTemperature",
                "WATER_TEMPER", "salinity", "speed", "tfvl", "free_kmh", "stopped_ratio", "precipitation_percent")
AUX_NAME = re.compile(r"(?i)(code|date|time|lat|lon|^id$|_nm$|^batt$|limit|window|_sec$|direct|drc|dir$)")


def _numberish(value: Any) -> Any:
    """'57', '.3' 처럼 숫자를 문자열로 주는 원천 데이터를 숫자로 바꾼다."""
    if isinstance(value, str) and _NUMBER.match(value.strip()):
        text = value.strip()
        return float(text) if "." in text else int(text)
    return value


def flatten(row: Dict[str, Any]) -> Dict[str, Any]:
    """데이터 한 행을 평평한 이름→값으로. 연합객체·NGSI-LD·원천 데이터 모두 처리한다."""
    data = row.get("data")
    # 원천 데이터 객체는 {"id","data":[측정값…],"status"} 처럼 한 번 더 감싸 준다.
    if isinstance(data, dict) and isinstance(data.get("data"), list) and set(data) <= {"id", "data", "status", "result"}:
        data = {"measurements": data["data"]}
    flat = brain.flatten_row({**row, "data": data if isinstance(data, (dict, list)) else {}})
    return {k: _numberish(v) for k, v in flat.items()}


def _type_of(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (list, dict)):
        return "list" if isinstance(value, list) else "object"
    return "string"


def _schema_properties(data_model: Any) -> Dict[str, str]:
    """디지털객체 데이터 모델(JSON 스키마)의 속성 이름과 타입."""
    props = (data_model or {}).get("properties") if isinstance(data_model, dict) else None
    out: Dict[str, str] = {}
    for name, spec in (props or {}).items():
        if name in ("id", "type", "@context"):
            continue
        if not isinstance(spec, dict):
            continue
        kind = spec.get("type", "")
        if kind == "object" and isinstance(spec.get("properties"), dict) and "value" in spec["properties"]:
            kind = spec["properties"]["value"].get("type", "object")  # NGSI-LD Property
        out[name] = kind or "any"
    return out


def _freshness(rowtime: Optional[str]) -> Tuple[str, Optional[float]]:
    if not rowtime:
        return "none", None
    try:
        stamp = datetime.fromisoformat(str(rowtime).replace("Z", "+00:00"))
    except ValueError:
        return "unknown", None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - stamp).total_seconds() / 3600
    if hours < 2:
        return "live", hours
    if hours < 24 * STALE_DAYS:
        return "recent", hours
    return "stale", hours


# ---------------------------------------------------------------------------
# 참조
# ---------------------------------------------------------------------------

def parse_ref(ref: str) -> Tuple[str, str, str]:
    parts = str(ref or "").split(":", 2)
    if len(parts) != 3 or parts[0] not in ("do", "fdo") or not parts[1] or not parts[2]:
        raise TwinError(f"트윈 참조 형식이 올바르지 않습니다: {ref}")
    return parts[0], parts[1], parts[2]


def latest_url(ref: str) -> str:
    kind, a, b = parse_ref(ref)
    return f"/api/twins/{kind}/{a}/{b}/latest"


def latest(ref: str) -> Dict[str, Any]:
    kind, a, b = parse_ref(ref)
    rows = digital_object_rows(a, b, 1) if kind == "do" else brain.object_rows(a, b, 1)
    if not rows:
        raise TwinError("이 트윈에는 아직 데이터가 없습니다.")
    return flatten(rows[0])


# ---------------------------------------------------------------------------
# 목록(카탈로그)
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_cache: Tuple[float, List[Dict[str, Any]], Dict[str, Dict[str, Any]]] = (0.0, [], {})


def _numeric_names(values: Dict[str, Any], schema: Dict[str, str]) -> List[str]:
    names = [k for k, v in values.items() if "." not in k and isinstance(v, (int, float)) and not isinstance(v, bool)]
    for name, kind in schema.items():  # 값이 아직 없어도 스키마가 숫자라고 하면 후보
        if kind in ("number", "integer") and name not in names:
            names.append(name)
    names = [n for n in names if not n.endswith("_id") and n not in ("devId", "rowtime")]
    # 측정값을 앞에, 식별자·코드·날짜·좌표·배터리 같은 부가 값을 뒤에 둔다(처음 고르는 출력 순서).
    rank = {n.lower(): i for i, n in enumerate(KEY_MEASURES)}
    return sorted(names, key=lambda n: (1 if AUX_NAME.search(n) else 0, rank.get(n.lower(), len(rank))))


def _do_entry(dt: Dict[str, Any], do: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        rows = digital_object_rows(dt["digital_twin_id"], do["digital_object_id"], 1)
    except TwinError:
        return None
    if not rows or not rows[0].get("data"):
        return None
    values = flatten(rows[0])
    schema = _schema_properties(do.get("digital_object_data_model"))
    numeric = _numeric_names(values, schema)
    if not numeric:
        return None  # 로직에서 판단·계산할 값이 없는 객체(빈 값, 문서형)는 노드로 내놓지 않는다
    fresh, _ = _freshness(rows[0].get("rowtime"))
    return {
        "ref": f"do:{dt['digital_twin_id']}:{do['digital_object_id']}",
        "kind": "do",
        "name": do.get("digital_object_name") or do["digital_object_id"],
        "twinId": dt["digital_twin_id"],
        "twinName": dt.get("digital_twin_name") or dt["digital_twin_id"],
        "owner": dt.get("owner") or "",
        "rowtime": rows[0].get("rowtime"),
        "freshness": fresh,
        "numeric": numeric,
        "schema": bool(schema),
    }


def _fdo_entry(fdt: Dict[str, Any], fdo: Dict[str, Any], do_twins: Dict[str, Dict[str, str]]) -> Optional[Dict[str, Any]]:
    try:
        rows = brain.object_rows(fdt["federated_digital_twin_id"], fdo["federated_digital_object_id"], 1)
    except brain.BrainError:
        return None
    if not rows:
        return None
    values = flatten(rows[0])
    numeric = _numeric_names(values, {})
    if not numeric:
        return None
    fresh, _ = _freshness(rows[0].get("rowtime"))
    members = fdo.get("member_digital_twin_object_ids") or []
    return {
        "ref": f"fdo:{fdt['federated_digital_twin_id']}:{fdo['federated_digital_object_id']}",
        "kind": "fdo",
        "name": fdo.get("federated_digital_object_name") or fdo["federated_digital_object_id"],
        "twinId": fdt["federated_digital_twin_id"],
        "twinName": fdt.get("federated_digital_twin_name") or fdt["federated_digital_twin_id"],
        "owner": fdt.get("owner") or "",
        "rowtime": rows[0].get("rowtime"),
        "freshness": fresh,
        "numeric": numeric,
        "members": [{"objectId": m, **do_twins.get(m, {})} for m in members],
    }


def catalog(refresh: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """노드로 쓸 수 있는 트윈 목록과 디지털객체→단일트윈 색인. 10분 캐시."""
    global _cache
    with _lock:
        stamp, entries, index = _cache
        if not refresh and entries and time.time() - stamp < CATALOG_TTL:
            return entries, index
        try:
            dts = digital_twins()
        except TwinError as exc:
            logger.info("트윈 목록을 가져오지 못했습니다: %s", exc)
            return entries, index
        pairs, index = [], {}
        for dt in dts:
            try:
                for do in digital_objects(dt["digital_twin_id"]):
                    pairs.append((dt, do))
                    index[do["digital_object_id"]] = {
                        "twinId": dt["digital_twin_id"], "twinName": dt.get("digital_twin_name") or "",
                        "owner": dt.get("owner") or "", "objectName": do.get("digital_object_name") or "",
                    }
            except TwinError:
                continue
        with ThreadPoolExecutor(max_workers=12) as pool:
            do_entries = [e for e in pool.map(lambda p: _do_entry(*p), pairs) if e]
        fdo_entries = []
        try:
            for fdt in brain.federated_twins():
                for fdo in brain.federated_objects(fdt.get("federated_digital_twin_id", "")):
                    entry = _fdo_entry(fdt, fdo, index)
                    if entry:
                        fdo_entries.append(entry)
        except brain.BrainError:
            pass
        entries = do_entries + fdo_entries
        _cache = (time.time(), entries, index)
        return entries, index


# ---------------------------------------------------------------------------
# 상세(속성 패널)
# ---------------------------------------------------------------------------

def detail(ref: str) -> Dict[str, Any]:
    """트윈 메타정보와 속성 목록(이름·타입·지금 값). 모두 프레임워크 API 조회 결과."""
    kind, a, b = parse_ref(ref)
    if kind == "do":
        twin = next((t for t in digital_twins() if t.get("digital_twin_id") == a), None)
        obj = next((o for o in digital_objects(a) if o.get("digital_object_id") == b), None)
        if twin is None or obj is None:
            raise TwinError("등록되지 않은 트윈입니다.")
        rows = digital_object_rows(a, b, 1)
        schema = _schema_properties(obj.get("digital_object_data_model"))
        meta = {
            "source": "Digital Connector (단일 트윈)",
            "twin": {k: twin.get(k) for k in ("digital_twin_id", "digital_twin_name", "description", "owner",
                                              "keywords", "point_of_access", "contact_point", "creation_time")},
            "object": {k: obj.get(k) for k in ("digital_object_id", "digital_object_name", "description",
                                               "keywords", "digital_object_data_access_type", "modification_time")},
        }
        members: List[Dict[str, Any]] = []
    else:
        fdt = next((t for t in brain.federated_twins() if t.get("federated_digital_twin_id") == a), None)
        fdo = next((o for o in brain.federated_objects(a) if o.get("federated_digital_object_id") == b), None)
        if fdt is None or fdo is None:
            raise TwinError("등록되지 않은 연합 객체입니다.")
        rows = brain.object_rows(a, b, 1)
        schema = {}
        _, index = catalog()
        members = [{"objectId": m, **index.get(m, {})} for m in fdo.get("member_digital_twin_object_ids") or []]
        meta = {
            "source": "Digital Brain (연합 객체)",
            "twin": {k: fdt.get(k) for k in ("federated_digital_twin_id", "federated_digital_twin_name",
                                             "description", "owner", "keywords")},
            "object": {k: fdo.get(k) for k in ("federated_digital_object_id", "federated_digital_object_name",
                                               "description", "keywords", "modification_time")},
        }

    values = flatten(rows[0]) if rows else {}
    names = list(dict.fromkeys([k for k in schema] + [k for k in values if "." not in k]))
    properties = []
    for name in names:
        if name in ("rowtime", "observedAt", "location", "devId") or name.endswith("_id"):
            continue
        value = values.get(name)
        if isinstance(value, (list, dict)):
            continue
        actual = _type_of(value) if value is not None else ""
        properties.append({
            "name": name,
            # 원천이 숫자를 문자열로 주는 경우가 있어 실제 값의 타입을 우선한다.
            "type": actual if actual == "number" else (schema.get(name) or actual or "any"),
            "schemaType": schema.get(name, ""),
            "value": value,
            "inSchema": name in schema,
            "aux": bool(AUX_NAME.search(name)),
        })
    fresh, hours = _freshness(rows[0].get("rowtime") if rows else None)
    return {
        "ref": ref,
        "kind": kind,
        **meta,
        "members": members,
        "rowtime": rows[0].get("rowtime") if rows else None,
        "observedAt": values.get("observedAt"),
        "freshness": fresh,
        "ageHours": round(hours, 1) if hours is not None else None,
        "properties": properties,
        "latestUrl": latest_url(ref),
    }


def linkage(refs: List[str]) -> Dict[str, Any]:
    """로직이 연계한 단일 트윈(메타정보 종) 목록. 연합 객체는 구성 디지털객체의 트윈으로 펼친다."""
    entries, index = catalog()
    by_ref = {e["ref"]: e for e in entries}
    twins: Dict[str, Dict[str, Any]] = {}
    unknown: List[str] = []
    for ref in dict.fromkeys(refs):
        try:
            kind, a, b = parse_ref(ref)
        except TwinError:
            unknown.append(ref)
            continue
        if kind == "do":
            info = index.get(b) or {}
            key = info.get("twinId") or a
            twins.setdefault(key, {"twinId": key, "twinName": info.get("twinName", ""), "owner": info.get("owner", ""),
                                   "via": []})["via"].append(info.get("objectName") or b)
        else:
            entry = by_ref.get(ref)
            members = (entry or {}).get("members") or []
            if not members:
                unknown.append(ref)
            for m in members:
                key = m.get("twinId") or m["objectId"]
                twins.setdefault(key, {"twinId": key, "twinName": m.get("twinName", ""), "owner": m.get("owner", ""),
                                       "via": []})["via"].append(f"{(entry or {}).get('name', b)} › {m.get('objectName') or m['objectId']}")
    return {"count": len(twins), "twins": list(twins.values()), "unresolved": unknown}
