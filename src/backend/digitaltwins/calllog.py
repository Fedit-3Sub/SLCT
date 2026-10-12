"""연합트윈 프레임워크 API 호출 기록.

메타정보·데이터를 외부(Digital Connector, Digital Brain, 2세부 메타데이터 저장소)에서
가져올 때마다 `slct.integration` 로거에 한 줄씩 남긴다. 운영에서는
`docker compose logs backend` 로 보고, 어떤 트윈의 메타정보를 실제로 조회했는지
확인하는 근거로 쓴다. 토큰과 응답 본문은 남기지 않는다.

    [연합트윈 API] Digital Connector GET http://…/fedit/v1/digital-twins/KR-01-…/digital-objects → 200 (3건, 85ms)

목록 캐시를 채울 때처럼 한꺼번에 수백 번 부르는 경우에는 `bulk()` 안에서 호출해
줄마다의 기록은 DEBUG 로 내리고 요약 한 줄만 INFO 로 남긴다.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger("slct.integration")

_state = threading.local()


def _bulk_depth() -> int:
    return getattr(_state, "bulk", 0)


class _Stats:
    def __init__(self):
        self.count = 0
        self.errors = 0
        self.lock = threading.Lock()

    def add(self, failed: bool) -> None:
        with self.lock:
            self.count += 1
            self.errors += 1 if failed else 0


@contextmanager
def bulk(label: str):
    """이 블록 안의 호출은 DEBUG 로 기록하고, 끝날 때 요약을 INFO 로 남긴다."""
    stats = _Stats()
    previous = getattr(_state, "stats", None)
    _state.bulk = _bulk_depth() + 1
    _state.stats = stats
    started = time.monotonic()
    try:
        yield
    finally:
        _state.bulk = _bulk_depth() - 1
        _state.stats = previous
        logger.info("[연합트윈 API] %s: 호출 %d건, 실패 %d건 (%dms)", label, stats.count, stats.errors,
                    round((time.monotonic() - started) * 1000))


def current_bulk() -> Optional[_Stats]:
    """작업 스레드에 넘겨줄 지금의 집계(없으면 None)."""
    return getattr(_state, "stats", None) if _bulk_depth() else None


@contextmanager
def bulk_worker(stats: Optional[_Stats]):
    """작업 스레드용: 바깥 `bulk()` 의 집계에 더하고, 줄마다의 기록은 DEBUG 로 내린다."""
    previous = getattr(_state, "stats", None)
    _state.bulk = _bulk_depth() + 1
    _state.stats = stats
    try:
        yield
    finally:
        _state.bulk = _bulk_depth() - 1
        _state.stats = previous


def _count(body: Any) -> Optional[int]:
    if isinstance(body, dict):
        body = body.get("data", body)
    if isinstance(body, list):
        return len(body)
    return None


def record(source: str, method: str, url: str, *, params: Optional[Dict[str, Any]] = None,
           status: Optional[int] = None, body: Any = None, error: str = "", started: Optional[float] = None) -> None:
    """외부 호출 한 건을 기록한다."""
    stats = getattr(_state, "stats", None)
    if stats is not None:
        stats.add(bool(error) or (status or 0) >= 400)
    full = f"{url}?{urlencode(params)}" if params else url
    elapsed = f", {round((time.monotonic() - started) * 1000)}ms" if started is not None else ""
    if error:
        level = logging.DEBUG if _bulk_depth() else logging.WARNING
        logger.log(level, "[연합트윈 API] %s %s %s → 실패: %s%s", source, method, full, error, elapsed)
        return
    n = _count(body)
    detail = f"{n}건" if n is not None else "응답"
    level = logging.DEBUG if _bulk_depth() else logging.INFO
    logger.log(level, "[연합트윈 API] %s %s %s → %s (%s%s)", source, method, full, status, detail, elapsed)


def run_summary(run_id: Any, diagram: str, twins: Dict[str, Any]) -> None:
    """로직 실행이 메타정보를 연계한 단일 트윈 요약. 트윈 이름·소유는 Digital Connector 의 트윈 메타정보다."""
    items = twins.get("twins", [])
    logger.info("[메타정보 연계] 실행 #%s %s: 단일 트윈 %d종 (메타정보 출처: Digital Connector 단일 트윈 등록 정보)",
                run_id, diagram or "-", twins.get("count", 0))
    for n, t in enumerate(items, 1):
        logger.info("[메타정보 연계]   %d. %s | 트윈 ID %s | 소유 %s | 연계 노드 %s", n,
                    t.get("twinName") or "-", t.get("twinId"), t.get("owner") or "-", " · ".join(t.get("via") or []))
    for ref in twins.get("unresolved") or []:
        logger.warning("[메타정보 연계]   확인되지 않은 트윈 참조: %s", ref)
