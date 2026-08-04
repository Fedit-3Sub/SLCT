"""코파일럿 생성 오케스트레이터.

생성 엔진을 우선순위대로 시도하고, 앞 단계가 불가능하면 다음 단계로 넘어간다.

    1. 외부 LLM 서버(Ollama 등)  — 설정이 있고 연결되는 경우
    2. 내장 CPU LLM (llama.cpp)  — 모델 파일이 준비된 경우
    3. 규칙 기반 생성기          — 항상 동작하는 최종 안전망

어느 경로를 타든 결과는 [bpmn_spec] 빌더를 통과하므로 XML 은 항상 유효하다.
좌표는 생성하지 않으며, 프런트엔드가 자동 레이아웃으로 노드를 배치한다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from . import local_llm, rule_based
from .bpmn_spec import normalize_spec, spec_to_bpmn_xml, summarize_spec
from .models import LlmConfig

logger = logging.getLogger(__name__)

# 외부 LLM 서버 연결 확인 제한시간(초) — 데모 응답성을 위해 짧게 잡는다.
PROBE_TIMEOUT = 1.5

ENGINE_LABELS = {
    "local-llm": "내장 CPU LLM",
    "rule-based": "규칙 기반 생성기",
}


def _probe_endpoint(base_url: str, timeout: float = PROBE_TIMEOUT) -> bool:
    """LLM 서버가 실제로 응답하는지 TCP 수준에서 빠르게 확인한다."""
    if not base_url:
        return False
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def remote_provider_available(config: Optional[LlmConfig]) -> bool:
    """설정된 외부 LLM 프로바이더에 연결할 수 있는지."""
    if config is None or not getattr(config, "enabled", False):
        return False
    # 클라우드 API 는 api_key 유무로 판단(네트워크 탐침은 의미가 적다).
    if config.provider in ("openai", "anthropic"):
        return bool(config.api_key)
    return _probe_endpoint(config.base_url or "")


def _select_engine(prompt: str, config: Optional[LlmConfig]) -> Dict[str, Any]:
    """가용한 엔진으로 spec 을 생성하고 사용한 엔진 정보를 함께 반환한다."""
    # 1) 외부 LLM 서버 — 연결은 확인하되 실제 호출은 아직 연결되지 않았다.
    #    (provider 별 호출 구현 시 이 자리에서 spec 을 받아오면 된다)
    remote_up = remote_provider_available(config)

    # 2) 내장 CPU LLM
    if local_llm.is_available():
        started = time.time()
        spec = local_llm.generate_spec(prompt)
        if spec:
            usage = spec.pop("_usage", {}) or {}
            return {
                "spec": spec,
                "engine": "local-llm",
                "remote_up": remote_up,
                "tokens_in": usage.get("tokens_in", 0),
                "tokens_out": usage.get("tokens_out", 0),
                "elapsed": time.time() - started,
            }
        logger.info("내장 LLM 생성 실패 — 규칙 기반으로 폴백")

    # 3) 규칙 기반 안전망
    started = time.time()
    return {
        "spec": rule_based.build_spec(prompt),
        "engine": "rule-based",
        "remote_up": remote_up,
        "tokens_in": max(1, len(prompt or "") // 4),
        "tokens_out": 0,
        "elapsed": time.time() - started,
    }


def generate_with_llm(prompt: str, config: Optional[LlmConfig], diagram_uid: str = "") -> Dict[str, Any]:
    """요구사항에서 BPMN 초안을 생성한다.

    반환 구조는 기존 API 계약을 그대로 유지한다
    (message / generatedXml / nodeSummary / tokens_* / cost / duration_ms).
    """
    start = time.time()

    try:
        selected = _select_engine(prompt or "", config)
        spec = normalize_spec(selected["spec"])
        xml = spec_to_bpmn_xml(spec)
    except Exception as exc:  # 어떤 경우에도 코파일럿이 죽지 않도록 방어
        logger.exception("BPMN 생성 실패")
        fallback = normalize_spec(rule_based.build_spec(prompt or ""))
        return {
            "message": "생성 중 문제가 발생하여 기본 초안을 제공합니다.",
            "generatedXml": spec_to_bpmn_xml(fallback),
            "nodeSummary": summarize_spec(fallback),
            "tokens_in": 0,
            "tokens_out": 0,
            "cost": 0,
            "duration_ms": int((time.time() - start) * 1000),
            "error": str(exc)[:500],
            "engine": "rule-based",
        }

    engine_label = ENGINE_LABELS.get(selected["engine"], selected["engine"])
    node_count = len(spec["nodes"])

    if selected["engine"] == "local-llm":
        note = "내장 CPU LLM 으로 생성했습니다."
    elif selected["remote_up"]:
        note = "규칙 기반 생성기로 초안을 만들었습니다."
    else:
        note = "외부 LLM 서버에 연결할 수 없어 규칙 기반 생성기로 초안을 만들었습니다."

    message = f"{spec['name']} 초안을 생성했습니다. 노드 {node_count}개. {note} ({engine_label})"

    return {
        "message": message,
        "generatedXml": xml,
        "nodeSummary": summarize_spec(spec),
        "tokens_in": selected["tokens_in"],
        "tokens_out": selected["tokens_out"],
        "cost": 0,
        "duration_ms": int((time.time() - start) * 1000),
        "engine": selected["engine"],
    }
