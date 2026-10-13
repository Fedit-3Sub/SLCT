"""로직 실행 요청을 받아 실행기를 돌리고 기록을 저장한다."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from django.db import close_old_connections
from django.utils import timezone

from digitaltwins import calllog, twins

from .engine import Engine, StepRecord
from .invoker import http_invoker
from .models import PipelineRun, PipelineStep

logger = logging.getLogger(__name__)

# 응답 원문은 디버깅용이므로 너무 크면 앞부분만 남긴다.
MAX_STORED_RESPONSE = 64 * 1024


def _fit(value: Any) -> Any:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)[:MAX_STORED_RESPONSE]
    if len(text) <= MAX_STORED_RESPONSE:
        return json.loads(text)
    return {"_truncated": True, "text": text[:MAX_STORED_RESPONSE]}


def _parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _save_step(run: PipelineRun, step: StepRecord) -> None:
    PipelineStep.objects.create(
        run=run,
        seq=step.seq,
        node_id=step.node_id[:128],
        node_type=step.node_type[:64],
        node_name=step.node_name[:255],
        scope_id=step.scope_id[:128],
        status=step.status,
        inputs=_fit(step.inputs),
        outputs=_fit(step.outputs),
        request=_fit(step.request),
        response=_fit(step.response),
        flows=step.flows,
        warnings=step.warnings,
        error=step.error,
        attempts=step.attempts,
        started_at=_parse_time(step.started_at),
        duration_ms=step.duration_ms,
    )


def execute(run: PipelineRun) -> PipelineRun:
    """실행 기록 하나를 실제로 실행한다. 단계는 끝나는 대로 저장한다."""
    run.status = "running"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    engine = Engine(http_invoker, on_step=lambda step: _save_step(run, step))
    try:
        result = engine.run(run.xml, run.inputs, run.start)
        run.status = result.status
        run.error = result.error
        run.variables = _fit(result.variables)
        run.result = _fit(result.result) if result.result is not None else None
    except Exception as exc:  # 실행기 버그라도 기록은 끝맺는다.
        logger.exception("로직 실행 중 예기치 않은 오류 (run=%s)", run.pk)
        run.status = "failed"
        run.error = f"실행기 내부 오류: {exc}"
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error", "variables", "result", "finished_at"])
    _log_linkage(run)
    return run


def _log_linkage(run: PipelineRun, background: bool = True) -> None:
    """이 실행이 메타정보를 연계한 단일 트윈을 로그에 남긴다(트윈 노드가 있을 때만).

    트윈 목록 캐시가 비어 있으면 목록을 새로 받느라 몇 초 걸리므로, 실행 응답을
    늦추지 않도록 따로 스레드에서 남긴다.
    """
    refs, labels = twins.refs_in_xml(run.xml, with_labels=True)
    if not refs:
        return
    run_id, diagram = run.pk, run.diagram_uid

    def target() -> None:
        try:
            calllog.run_summary(run_id, diagram, twins.linkage(refs, labels))
        except Exception:  # 기록 실패가 실행 결과에 영향을 주면 안 된다.
            logger.debug("연계 트윈 요약을 남기지 못했습니다 (run=%s)", run_id, exc_info=True)

    if background:
        threading.Thread(target=target, name=f"pipeline-linkage-{run_id}", daemon=True).start()
    else:
        target()


def execute_in_background(run_id: int) -> None:
    def target() -> None:
        close_old_connections()
        try:
            execute(PipelineRun.objects.get(pk=run_id))
        finally:
            close_old_connections()

    threading.Thread(target=target, name=f"pipeline-run-{run_id}", daemon=True).start()


def serialize_step(step: PipelineStep) -> Dict[str, Any]:
    return {
        "seq": step.seq,
        "nodeId": step.node_id,
        "nodeType": step.node_type,
        "nodeName": step.node_name,
        "scopeId": step.scope_id,
        "status": step.status,
        "inputs": step.inputs,
        "outputs": step.outputs,
        "request": step.request,
        "response": step.response,
        "flows": step.flows,
        "warnings": step.warnings,
        "error": step.error,
        "attempts": step.attempts,
        "startedAt": step.started_at.isoformat() if step.started_at else None,
        "durationMs": step.duration_ms,
    }


def serialize_run(run: PipelineRun, with_steps: bool = True) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": run.pk,
        "diagramUid": run.diagram_uid,
        "status": run.status,
        "trigger": run.trigger,
        "start": run.start,
        "inputs": run.inputs,
        "variables": run.variables,
        "result": run.result,
        "error": run.error,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
    }
    if run.started_at and run.finished_at:
        data["durationMs"] = int((run.finished_at - run.started_at).total_seconds() * 1000)
    if with_steps:
        data["steps"] = [serialize_step(s) for s in run.steps.all()]
    return data
