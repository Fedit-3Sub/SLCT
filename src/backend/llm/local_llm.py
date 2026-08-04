"""CPU 로 동작하는 내장 LLM 프로바이더 (llama.cpp / GGUF).

Ollama 같은 외부 LLM 서버에 연결할 수 없을 때 사용하는 자체 생성기다.
GPU 없이 CPU 만으로 동작하며, **GBNF 문법 제약 디코딩**으로 출력이 반드시
정해진 JSON 스키마를 따르도록 강제한다. 소형 모델이 흔히 내놓는 깨진 출력
문제를 근본적으로 막기 위한 장치다.

모델 파일(GGUF)은 저장소에 포함하지 않는다. `LOCAL_LLM_MODEL_PATH` 환경변수
또는 기본 경로(`src/backend/models/*.gguf`)에서 찾고, 없으면 이 프로바이더는
사용 불가로 처리되어 규칙 기반 생성기가 대신 응답한다.

권장 모델: Qwen2.5-1.5B-Instruct GGUF (Q4_K_M, 약 1GB, Apache-2.0)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .bpmn_spec import NODE_TYPES, parse_spec_json

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = BASE_DIR / "models"

# 출력 구조를 강제하는 GBNF 문법. 모델은 이 형태 밖의 토큰을 생성할 수 없다.
_NODE_TYPE_RULE = " | ".join(f'"\\"{t}\\""' for t in NODE_TYPES)
# 주의: llama.cpp 의 GBNF 파서는 규칙을 여러 줄로 나눠 쓰는 것을 허용하지 않는다.
# 줄바꿈으로 이어쓰면 파싱이 실패하고 네이티브 계층에서 프로세스가 죽을 수 있으므로
# 규칙 하나는 반드시 한 줄로 유지할 것.
BPMN_GRAMMAR = "\n".join([
    r'root ::= "{" ws "\"name\":" ws string "," ws "\"nodes\":" ws nodes "," ws "\"flows\":" ws flows ws "}"',
    # 노드 수를 3~8개로 문법 차원에서 제한한다. 소형 모델은 프롬프트의 개수 지시를
    # 자주 무시하는데, 이 제약이 출력 길이(=응답 지연)와 주제 이탈을 함께 억제한다.
    r'nodes ::= "[" ws node (ws "," ws node){2,7} ws "]"',
    r'node ::= "{" ws "\"id\":" ws string "," ws "\"type\":" ws nodetype "," ws "\"name\":" ws string ws "}"',
    r'flows ::= "[" ws "]" | "[" ws flow (ws "," ws flow)* ws "]"',
    r'flow ::= "{" ws "\"from\":" ws string "," ws "\"to\":" ws string "," ws "\"name\":" ws string ws "}"',
    "nodetype ::= " + _NODE_TYPE_RULE,
    r'string ::= "\"" char* "\""',
    r'char ::= [^"\\] | "\\" ["\\bfnrt]',
    r'ws ::= [ \t\n]*',
    "",
])

SYSTEM_PROMPT = (
    "당신은 BPMN 프로세스 설계 도우미입니다. "
    "사용자의 요구사항을 읽고 업무 흐름을 JSON 으로만 출력하세요.\n"
    "규칙:\n"
    "1. nodes 는 startEvent 로 시작해 endEvent 로 끝나며 4~8개로 구성합니다.\n"
    "2. 일반 처리 단계는 task, 외부 시스템 호출·데이터 수집은 serviceTask, "
    "알림·메시지 발송은 sendTask 를 사용합니다.\n"
    "3. 게이트웨이는 흐름이 실제로 갈라질 때만 씁니다. "
    "조건에 따라 한 갈래만 선택하면 exclusiveGateway, "
    "여러 갈래를 동시에 수행하면 parallelGateway 입니다. "
    "단순한 순차 단계에는 게이트웨이를 쓰지 마세요.\n"
    "4. flows 는 모든 노드를 빠짐없이 연결해야 합니다.\n"
    "5. 모든 이름(name)은 한국어로 간결하게 작성합니다."
)


def _physical_cores() -> int:
    """물리 코어 수를 추정한다.

    llama.cpp 는 물리 코어 수만큼 스레드를 쓸 때 가장 빠르다. 하이퍼스레딩
    논리 코어까지 모두 쓰면 경합으로 오히려 느려진다(측정: 16스레드 69초 vs 8스레드 18초).
    """
    try:
        cores = set()
        with open("/proc/cpuinfo") as fh:
            physical_id = core_id = None
            for line in fh:
                if line.startswith("physical id"):
                    physical_id = line.split(":")[1].strip()
                elif line.startswith("core id"):
                    core_id = line.split(":")[1].strip()
                elif not line.strip() and physical_id is not None and core_id is not None:
                    cores.add((physical_id, core_id))
                    physical_id = core_id = None
            if physical_id is not None and core_id is not None:
                cores.add((physical_id, core_id))
        if cores:
            return len(cores)
    except OSError:
        pass
    logical = os.cpu_count() or 4
    return max(1, logical // 2)

_model = None
_model_lock = threading.Lock()
_load_failed = False


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def find_model_path() -> Optional[Path]:
    """사용할 GGUF 모델 경로를 찾는다. 없으면 None."""
    configured = os.environ.get("LOCAL_LLM_MODEL_PATH")
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_file() else None
    model_dir = Path(os.environ.get("LOCAL_LLM_MODEL_DIR", DEFAULT_MODEL_DIR)).expanduser()
    if not model_dir.is_dir():
        return None
    candidates = sorted(model_dir.glob("*.gguf"))
    return candidates[0] if candidates else None


def is_enabled() -> bool:
    """내장 LLM 사용 여부. 끄면 규칙 기반 생성기만 쓰여 즉시 응답한다.

    소형 모델 추론은 CPU 에서 수십 초가 걸리므로, 응답 속도가 중요한 환경에서는
    `LOCAL_LLM_ENABLED=0` 으로 비활성화할 수 있다.
    """
    return os.environ.get("LOCAL_LLM_ENABLED", "1").strip().lower() not in ("0", "false", "no")


def is_available() -> bool:
    """런타임(llama-cpp-python)과 모델 파일이 모두 준비됐는지."""
    if _load_failed or not is_enabled():
        return False
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return find_model_path() is not None


def status() -> Dict[str, Any]:
    """진단용 상태 정보."""
    try:
        import llama_cpp  # noqa: F401
        runtime = True
    except ImportError:
        runtime = False
    path = find_model_path()
    return {
        "enabled": is_enabled(),
        "runtime_installed": runtime,
        "model_path": str(path) if path else None,
        "loaded": _model is not None,
        "threads": _env_int("LOCAL_LLM_THREADS", _physical_cores()),
        "available": bool(runtime and path and not _load_failed and is_enabled()),
    }


def _get_model():
    """모델을 지연 로드한다(최초 1회). 실패하면 이후 재시도하지 않는다."""
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        return None
    with _model_lock:
        if _model is not None:
            return _model
        if _load_failed:
            return None
        path = find_model_path()
        if path is None:
            _load_failed = True
            return None
        try:
            from llama_cpp import Llama

            started = time.time()
            _model = Llama(
                model_path=str(path),
                n_ctx=_env_int("LOCAL_LLM_CTX", 2048),
                n_threads=_env_int("LOCAL_LLM_THREADS", _physical_cores()),
                n_gpu_layers=_env_int("LOCAL_LLM_GPU_LAYERS", 0),  # 기본 CPU 전용
                verbose=False,
            )
            logger.info("로컬 LLM 로드 완료: %s (%.1fs)", path.name, time.time() - started)
        except Exception:  # 모델 손상/메모리 부족 등 — 폴백으로 넘긴다.
            logger.exception("로컬 LLM 로드 실패: %s", path)
            _load_failed = True
            return None
    return _model


def generate_spec(prompt: str) -> Optional[Dict[str, Any]]:
    """요구사항에서 BPMN spec 을 생성한다. 실패하면 None(규칙 기반으로 폴백)."""
    model = _get_model()
    if model is None:
        return None

    try:
        from llama_cpp import LlamaGrammar

        grammar = LlamaGrammar.from_string(BPMN_GRAMMAR, verbose=False)
        result = model.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (prompt or "").strip()[:2000]},
            ],
            grammar=grammar,
            max_tokens=_env_int("LOCAL_LLM_MAX_TOKENS", 768),
            temperature=0.3,
        )
    except Exception:
        logger.exception("로컬 LLM 생성 실패")
        return None

    text = ""
    try:
        text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        logger.warning("로컬 LLM 응답 구조가 예상과 다름")
        return None

    spec = parse_spec_json(text)
    if not spec:
        logger.warning("로컬 LLM 출력에서 spec JSON 을 얻지 못함")
        return None

    usage = result.get("usage") or {}
    spec["_usage"] = {
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
    }
    return spec
