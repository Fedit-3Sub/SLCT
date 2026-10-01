"""연합트윈 메타데이터 API 클라이언트.

디지털트윈과 시뮬레이션 메타데이터를 조회한다. 인증은 Bearer JWT 이며,
토큰이 없거나 서버에 연결할 수 없으면 조회를 시도하지 않고 호출자가
[catalog] 의 기본 목록으로 대체하도록 한다.

환경변수
    FEDIT_META_BASE_URL  메타데이터 API 주소 (기본 http://220.124.222.86:16997)
    FEDIT_META_TOKEN     Bearer 토큰. **비어 있으면 이 클라이언트는 비활성**
    FEDIT_META_TIMEOUT   요청 제한시간(초, 기본 5)

토큰은 자격증명이므로 저장소에 두지 않는다. 환경변수나 배포 시크릿으로 주입한다.

주요 경로 (Swagger: {base}/meta/swagger-ui/index.html)
    GET /meta/api/v1/resource/digitalTwins             디지털트윈 목록
    GET /meta/api/v1/resource/digitalTwins/{id}        디지털트윈 상세
    GET /meta/api/v1/resource/sensors | controllers    센서·제어기 목록
    GET /meta/api/v1/resource/simulations              시뮬레이션 목록
    GET /meta/api/v1/resource/simulations/{id}         시뮬레이션 상세
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://220.124.222.86:16997"
# 메타데이터 등록 과정에서 표준 모델과 속성명이 달라진 경우가 있어 후보를 순서대로 확인한다.
NAME_KEYS = ("simulationName", "name", "dtName", "title")


def base_url() -> str:
    return os.environ.get("FEDIT_META_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def token() -> str:
    return (os.environ.get("FEDIT_META_TOKEN") or "").strip()


def is_configured() -> bool:
    """토큰이 설정돼 있어 실제 조회를 시도할 수 있는 상태인지."""
    return bool(token())


def _timeout() -> float:
    try:
        return float(os.environ.get("FEDIT_META_TIMEOUT", 5))
    except (TypeError, ValueError):
        return 5.0


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    if not is_configured():
        return None
    url = f"{base_url()}/meta/api/v1{path}"
    try:
        response = requests.get(
            url,
            params=params or {},
            headers={"Authorization": f"Bearer {token()}"},
            timeout=_timeout(),
        )
    except requests.RequestException as exc:
        logger.warning("연합트윈 메타데이터 요청 실패(%s): %s", path, exc)
        return None

    if response.status_code == 401:
        logger.warning("연합트윈 메타데이터 인증 실패 — 토큰을 확인하세요.")
        return None
    if not response.ok:
        logger.warning("연합트윈 메타데이터 응답 오류(%s): HTTP %s", path, response.status_code)
        return None
    try:
        return response.json()
    except ValueError:
        logger.warning("연합트윈 메타데이터 응답을 JSON 으로 해석할 수 없음(%s)", path)
        return None


def _pick(item: Dict[str, Any], keys) -> str:
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return ""


def _iter_items(payload: Any) -> List[Dict[str, Any]]:
    """응답 구조가 환경마다 달라 목록으로 보이는 지점을 찾아 반환한다."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "list", "items", "content", "results", "resource"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            nested = _iter_items(value)
            if nested:
                return nested
    return []


# 메타데이터 저장소의 리소스 이름(dataUri). 2026-10 기준 운영 서버에서 응답하는 것.
RESOURCES = {
    "digitalTwins": "디지털 트윈",
    "sensors": "센서",
    "controllers": "제어기",
    "simulations": "시뮬레이션",
}
ID_KEYS = ("simulationId", "dtsimid", "id", "digitalTwinId", "dtid", "medataSetId")


def list_resource(resource: str, page_size: int = 100) -> List[Dict[str, Any]]:
    """메타데이터 리소스 목록(원본 항목). 실패하면 빈 목록."""
    payload = _get(f"/resource/{resource}", {"curPage": 1, "pageListSize": page_size})
    return _iter_items(payload)


def summarize(item: Dict[str, Any]) -> Dict[str, Any]:
    """메타데이터 항목에서 화면·노드에 쓸 공통 필드만 고른다."""
    return {
        "id": _pick(item, ID_KEYS),
        "name": _pick(item, NAME_KEYS),
        "metaModel": item.get("metaModel") or "",
        "description": item.get("description") or "",
        "keywords": item.get("keywords") or [],
        "owner": item.get("owner") or "",
        "digitalTwinId": item.get("digitalTwinId") or item.get("dtid") or "",
        "accessUrl": item.get("simulationAccessURL") or item.get("url") or "",
    }


def list_simulations(page_size: int = 50) -> List[Dict[str, Any]]:
    """실행 주소가 있는 시뮬레이션만 카탈로그 항목 형태로 반환한다.

    메타데이터에만 등록되고 실행 주소(simulationAccessURL)가 없는 시뮬레이션은
    노드로 실행할 수 없으므로 여기서 제외한다(내장 카탈로그가 그대로 쓰인다).
    """
    entries: List[Dict[str, Any]] = []
    for index, item in enumerate(list_resource("simulations", page_size), start=1):
        info = summarize(item)
        if not info["name"] or not info["accessUrl"]:
            continue
        entries.append({
            "id": index,
            "name": info["name"][:128],
            "category": str(item.get("category") or "연합트윈"),
            "url": info["accessUrl"],
            "meta": {"simulationId": info["id"], "twinId": info["digitalTwinId"], "source": "fedit"},
        })
    return entries


def get_digital_twin(digital_twin_id: str) -> Optional[Dict[str, Any]]:
    """디지털트윈 상세 메타데이터."""
    if not digital_twin_id:
        return None
    payload = _get(
        f"/resource/digitalTwins/{digital_twin_id}",
        {"arrayDataLimitYn": "Y", "arrayDataLimit": 50},
    )
    return payload if isinstance(payload, dict) else None


def status() -> Dict[str, Any]:
    """진단용 상태 정보(토큰 값은 노출하지 않는다)."""
    return {
        "base_url": base_url(),
        "token_configured": is_configured(),
        "timeout": _timeout(),
    }
