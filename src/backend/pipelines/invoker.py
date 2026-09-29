"""로직 실행기가 노드 URL 을 호출하는 방법.

- `/api/pipelines/run?id=...` : 카탈로그 모의 응답을 프로세스 안에서 바로 만든다
- 그 밖의 상대 경로           : PIPELINE_BASE_URL 기준으로 붙여 호출한다
- http(s) 주소                : 그대로 호출한다

GET 은 입력값을 질의 문자열로, 그 밖의 메서드는 JSON 본문으로 보낸다.
메서드를 지정하지 않으면 입력이 있을 때 POST, 없을 때 GET 으로 본다.
"""

from __future__ import annotations

import os
from typing import Any, Dict
from urllib.parse import parse_qsl, urljoin, urlsplit

import requests

from . import mock
from .engine import CallResult, ExecutionError, NodeConfig

BASE_URL = os.environ.get("PIPELINE_BASE_URL", "http://127.0.0.1:1337")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def _method(config: NodeConfig, inputs: Dict[str, Any]) -> str:
    if config.method:
        return config.method
    return "POST" if inputs else "GET"


def http_invoker(config: NodeConfig, inputs: Dict[str, Any]) -> CallResult:
    url = config.url
    method = _method(config, inputs)

    if mock.is_mock_url(url):
        sim_id = mock.mock_id(url)
        return CallResult(
            response=mock.outputs_for(sim_id, inputs),
            status_code=200,
            request={"method": method, "url": url, "mock": True},
        )

    if not urlsplit(url).scheme:
        url = urljoin(BASE_URL.rstrip("/") + "/", url.lstrip("/"))
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ExecutionError(f"지원하지 않는 주소입니다: {config.url}")

    request_info: Dict[str, Any] = {"method": method, "url": url}
    kwargs: Dict[str, Any] = {"timeout": config.timeout or 30}
    if method == "GET":
        params = dict(parse_qsl(parts.query))
        params.update({k: v for k, v in inputs.items() if v is not None})
        kwargs["params"] = params
        url = parts._replace(query="").geturl()
        request_info["params"] = params
    else:
        kwargs["json"] = inputs
        request_info["body"] = inputs

    try:
        resp = requests.request(method, url, **kwargs)
    except requests.Timeout as exc:
        raise ExecutionError(f"{config.timeout:g}초 안에 응답이 없습니다: {url}") from exc
    except requests.RequestException as exc:
        raise ExecutionError(f"호출하지 못했습니다: {url} ({exc.__class__.__name__})") from exc

    text = resp.text[:MAX_RESPONSE_BYTES]
    try:
        body: Any = resp.json()
    except ValueError:
        body = text
    if resp.status_code >= 400:
        snippet = text[:200].replace("\n", " ")
        raise ExecutionError(f"HTTP {resp.status_code}: {url} {snippet}")
    return CallResult(response=body, status_code=resp.status_code, request=request_info)
