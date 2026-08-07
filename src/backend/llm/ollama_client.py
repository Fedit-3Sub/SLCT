"""Ollama 서버 연동 클라이언트.

외부 LLM 서버가 있을 때 사용하는 1순위 생성 경로다. Ollama 의 구조화 출력
(`format` 에 JSON 스키마 전달)으로 응답이 반드시 정해진 형태를 따르게 하여,
내장 LLM 과 동일한 spec 을 받아 같은 빌더로 XML 을 조립한다.

성능 참고(RTX 4090, gemma4 8B 기준 실측):
    - 콜드 스타트(모델 적재 포함): 약 150초
    - 웜 상태: 약 5초 (165 tok/s)
모델 적재 때문에 첫 요청이 크게 느리므로 타임아웃을 넉넉히 잡고,
초과하면 상위 호출자가 다음 엔진으로 폴백한다.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from .bpmn_spec import NODE_TYPES, parse_spec_json

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"

# 임베딩 전용 모델은 대화 생성에 쓸 수 없으므로 목록에서 제외한다.
EMBEDDING_HINTS = ("embed", "bge", "e5-", "gte-")

BASE_SYSTEM_PROMPT = (
    "당신은 BPMN 프로세스 설계 전문가입니다. "
    "사용자의 요구사항을 분석해 실무에서 쓸 수 있는 업무 흐름을 JSON 으로 설계하세요.\n"
    "- startEvent 로 시작해 endEvent 로 끝나며 5~10개의 단계로 구성합니다.\n"
    "- 외부 시스템 호출·데이터 수집은 serviceTask, 알림·메시지 발송은 sendTask, "
    "일반 처리는 task 를 사용합니다.\n"
    "- 흐름이 실제로 갈라질 때만 게이트웨이를 사용합니다"
    "(택일은 exclusiveGateway, 동시 수행은 parallelGateway).\n"
    "- flows 는 모든 노드를 빠짐없이 연결해야 합니다.\n"
    "- 모든 이름(name)은 한국어로 구체적으로 작성합니다."
)

CATALOG_GUIDE = (
    "\n\n[등록된 시뮬레이터·연계 서비스]\n"
    "{catalog}\n\n"
    "위 목록에 요구사항과 맞는 항목이 있으면 해당 단계의 catalogId 에 목록의 이름을 "
    "**정확히 그대로** 적으세요. 그러면 실행에 필요한 호출 정보가 자동으로 연결됩니다.\n"
    "맞는 항목이 없으면 catalogId 는 빈 문자열로 두고 name 만 자유롭게 작성하세요."
)


def system_prompt() -> str:
    """카탈로그 목록을 포함한 시스템 프롬프트."""
    try:
        from digitaltwins import catalog

        listing = catalog.prompt_catalog()
    except Exception:
        listing = ""
    if not listing:
        return BASE_SYSTEM_PROMPT
    return BASE_SYSTEM_PROMPT + CATALOG_GUIDE.format(catalog=listing)

# Ollama 에 전달할 응답 스키마 — 내장 LLM 의 GBNF 문법과 같은 구조를 강제한다.
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": list(NODE_TYPES)},
                    "name": {"type": "string"},
                    # 등록된 시뮬레이터·서비스를 지목하면 실행 URL 이 자동 연결된다.
                    "catalogId": {"type": "string"},
                },
                "required": ["id", "type", "name"],
            },
        },
        "flows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["from", "to"],
            },
        },
    },
    "required": ["name", "nodes", "flows"],
}


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def normalize_base_url(base_url: Optional[str]) -> str:
    url = (base_url or "").strip() or DEFAULT_BASE_URL
    if "://" not in url:
        url = f"http://{url}"
    return url.rstrip("/")


def list_models(base_url: Optional[str] = None, timeout: float = 3.0) -> List[Dict[str, Any]]:
    """서버에 적재 가능한 생성용 모델 목록을 조회한다. 실패하면 빈 목록."""
    url = f"{normalize_base_url(base_url)}/api/tags"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    models = []
    for item in payload.get("models", []) or []:
        name = item.get("name") or ""
        if not name or any(hint in name.lower() for hint in EMBEDDING_HINTS):
            continue
        details = item.get("details") or {}
        models.append({
            "name": name,
            "size": item.get("size", 0),
            "family": details.get("family", ""),
            "parameter_size": details.get("parameter_size", ""),
        })
    return models


def list_running(base_url: Optional[str] = None, timeout: float = 2.0) -> List[str]:
    """현재 메모리에 적재돼 있는(웜) 모델 이름 목록."""
    try:
        response = requests.get(f"{normalize_base_url(base_url)}/api/ps", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []
    return [m.get("name") for m in payload.get("models", []) or [] if m.get("name")]


def pick_model(base_url: Optional[str] = None) -> str:
    """설정에 모델이 지정되지 않았을 때 사용할 모델을 고른다.

    적재가 끝난 모델은 즉시 응답하지만(실측 약 5초), 적재되지 않은 대형 모델은
    첫 요청에서 수십~수백 초가 걸린다. 따라서 웜 모델을 최우선으로, 없으면
    가장 작은(=적재와 추론이 빠른) 모델을 고른다.
    """
    models = list_models(base_url)
    if not models:
        return ""
    running = set(list_running(base_url))
    warm = [m for m in models if m["name"] in running]
    if warm:
        return min(warm, key=lambda m: m.get("size") or 0)["name"]
    return min(models, key=lambda m: m.get("size") or 0)["name"]


def is_reachable(base_url: Optional[str] = None, timeout: float = 2.0) -> bool:
    """Ollama 서버가 응답하는지 확인한다."""
    try:
        response = requests.get(f"{normalize_base_url(base_url)}/api/tags", timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def generate_spec(prompt: str, model: str, base_url: Optional[str] = None,
                  api_key: str = "") -> Optional[Dict[str, Any]]:
    """Ollama 로 BPMN spec 을 생성한다. 실패하면 None(다음 엔진으로 폴백)."""
    if not model:
        return None

    url = f"{normalize_base_url(base_url)}/api/chat"
    body = {
        "model": model,
        "stream": False,
        # 추론 과정을 본문에 섞지 않도록 사고 모드를 끈다(지원 모델 한정).
        "think": False,
        "format": RESPONSE_SCHEMA,
        "options": {"temperature": 0.4},
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": (prompt or "").strip()[:4000]},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    # 모델 적재(콜드 스타트)까지 감안한 여유 있는 제한시간.
    timeout = _env_int("OLLAMA_TIMEOUT", 180)

    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Ollama 요청 실패(%s): %s", model, exc)
        return None
    except ValueError:
        logger.warning("Ollama 응답을 JSON 으로 해석할 수 없음(%s)", model)
        return None

    content = (payload.get("message") or {}).get("content") or ""
    spec = parse_spec_json(content)
    if not spec:
        logger.warning("Ollama 출력에서 spec 을 얻지 못함(%s)", model)
        return None

    spec["_usage"] = {
        "tokens_in": payload.get("prompt_eval_count", 0) or 0,
        "tokens_out": payload.get("eval_count", 0) or 0,
    }
    return spec
