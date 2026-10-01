"""저장한 서비스 로직을 API 로 공개하고 연합트윈(FeDiT)에 연결한다.

    GET  /api/logics                        공개 가능한 로직 목록
    POST /api/logics/{uid}/invoke           로직 실행(동기). 응답 = 결과
    GET  /api/logics/{uid}/spec             로직 API 의 OpenAPI 문서(자동 생성)
    GET  /api/logics/{uid}/fedit            연합트윈 시뮬레이션 등록 상태
    POST /api/logics/{uid}/fedit            연합트윈 시뮬레이션으로 등록

연합트윈 Digital Brain 은 등록된 시뮬레이션의 `simulation_access_url` 로
다음 형태를 POST 하고, 응답 본문을 시뮬레이션 결과로 저장한다.

    {
      "simulation_id": "...", "federated_digital_twin_id": "...",
      "simulation_name": "...", "simulation_subject": ["<연합객체 id>"],
      "input_data": [ {"federated_digital_object_id": "...", "data": {...NGSI-LD...}, "rowtime": "..."} ]
    }

invoke 는 이 형태를 알아보고 input_data 를 평평한 값(`pm10`, `temp` …)으로 풀어
로직의 입력으로 넣는다. 그 밖의 JSON 객체는 그대로 입력값이 된다.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bpmns.models import BpmnDiagram
from digitaltwins import brain

from . import runner
from .engine import ModelError, describe_interface
from .models import PipelineRun

FEDIT_META_KEYS = (
    "simulation_id", "federated_digital_twin_id", "simulation_name",
    "simulation_subject", "simulation_attribute", "simulation_data_id", "time_step", "rowtime",
)


def fedit_register_enabled() -> bool:
    return os.environ.get("SLCT_FEDIT_REGISTER", "").strip().lower() in ("1", "true", "yes")


def public_base_url(request) -> str:
    """외부(연합트윈)에서 이 백엔드를 부를 주소. SLCT_PUBLIC_URL 이 우선한다."""
    configured = os.environ.get("SLCT_PUBLIC_URL", "").strip().rstrip("/")
    return configured or request.build_absolute_uri("/").rstrip("/")


def invoke_url(request, uid: str) -> str:
    return f"{public_base_url(request)}/api/logics/{uid}/invoke"


def inputs_from_body(body: Any) -> Dict[str, Any]:
    """호출 본문을 로직 입력값으로 바꾼다."""
    if not isinstance(body, dict):
        return {"input": body}
    if "input_data" not in body:
        return dict(body)

    # 연합트윈 시뮬레이션 호출
    inputs: Dict[str, Any] = {k: body[k] for k in FEDIT_META_KEYS if k in body}
    raw = body.get("input_data")
    rows = raw if isinstance(raw, list) else [raw]
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("data"), (dict, list)):
            inputs.update({k: v for k, v in brain.flatten_row(row).items() if "." not in k})
        elif isinstance(row, dict):
            inputs.update(row)  # 수동 호출: 본문이 그대로 input_data 가 된다
    inputs["input_data"] = raw
    return inputs


def _typed(text: str) -> Any:
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def _diagram(uid: str):
    return BpmnDiagram.objects.filter(uid=uid).first()


class LogicListView(APIView):
    def get(self, request):
        items = []
        for diagram in BpmnDiagram.objects.order_by("-updated_at")[:200]:
            try:
                interface = describe_interface(diagram.xml)
            except ModelError:
                continue  # 실행할 수 없는 다이어그램은 공개 대상이 아니다.
            items.append({
                "uid": diagram.uid,
                "title": diagram.title,
                "updatedAt": diagram.updated_at.isoformat(),
                "invokeUrl": invoke_url(request, diagram.uid),
                "specUrl": f"{public_base_url(request)}/api/logics/{diagram.uid}/spec",
                "inputs": interface["inputs"],
                "outputs": interface["outputs"],
                "fedit": (diagram.metadata or {}).get("fedit"),
            })
        return Response({"data": items, "meta": {"count": len(items)}})


class LogicInvokeView(APIView):
    """로직 실행. 결과(종료 이벤트에 정의한 값, 없으면 전체 값)를 돌려준다."""

    def post(self, request, uid: str):
        diagram = _diagram(uid)
        if diagram is None:
            return Response({"error": f"로직 '{uid}' 를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        body = request.data
        inputs = inputs_from_body(body)
        trigger = "fedit" if isinstance(body, dict) and "input_data" in body else "api"

        run = PipelineRun.objects.create(
            diagram=diagram, diagram_uid=uid, xml=diagram.xml, inputs=runner._fit(inputs), trigger=trigger,
        )
        runner.execute(run)

        if run.status != "succeeded":
            return Response(
                {"data": {"runId": run.pk, "status": run.status, "error": run.error}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        result = run.result
        if result is None:
            result = {k: v for k, v in (run.variables or {}).items() if k != "input_data"}
        return Response({"data": {"runId": run.pk, "status": run.status, "result": result}})


class LogicSpecView(APIView):
    """로직 API 매뉴얼(OpenAPI 3). 저장할 때마다 다이어그램에서 다시 만든다."""

    def get(self, request, uid: str):
        diagram = _diagram(uid)
        if diagram is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            interface = describe_interface(diagram.xml)
        except ModelError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        title = diagram.title or uid
        defaults = interface.get("defaults", {})
        input_props = {}
        for name in interface["inputs"]:
            prop: Dict[str, Any] = {"description": f"로직 입력 '{name}'"}
            if name in defaults:
                prop["description"] += f" (선택, 기본값 {defaults[name]})"
                prop["example"] = _typed(defaults[name])
            input_props[name] = prop
        result_props = ({name: {"description": f"결과 '{name}'"} for name in interface["outputs"]}
                        or {"(전체 값)": {"description": "종료 이벤트에 결과를 정의하지 않아 실행 중 만들어진 값이 모두 담긴다."}})
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": f"{title} 서비스 로직 API",
                "version": diagram.updated_at.strftime("%Y%m%d%H%M%S"),
                "description": (
                    "서비스 로직 생성 도구에서 만든 로직을 호출한다. 본문의 값이 로직 입력이 되며, "
                    "연합트윈 시뮬레이션 호출 형식(input_data)도 받는다."
                ),
            },
            "servers": [{"url": public_base_url(request)}],
            "paths": {
                f"/api/logics/{uid}/invoke": {
                    "post": {
                        "summary": f"{title} 실행",
                        "requestBody": {
                            "required": False,
                            "content": {"application/json": {"schema": {
                                "type": "object", "properties": input_props, "additionalProperties": True,
                            }}},
                        },
                        "responses": {
                            "200": {"description": "실행 성공", "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {"data": {"type": "object", "properties": {
                                    "runId": {"type": "integer"},
                                    "status": {"type": "string"},
                                    "result": {"type": "object", "properties": result_props},
                                }}},
                            }}}},
                            "422": {"description": "실행 실패(노드 호출 오류, 만족하는 분기 없음 등)"},
                        },
                    }
                }
            },
        }
        return Response(spec)


class LogicFeditView(APIView):
    """로직을 연합트윈 시뮬레이션으로 등록한다.

    등록하면 Digital Brain 이 대상 연합객체 데이터를 time_step 주기로 모아 이 로직의
    invoke 주소로 보내고, 응답을 시뮬레이션 결과로 저장한다.

    본문: {"fdt": "<연합트윈 id>", "subjects": ["<연합객체 id>"], "timeStep": 1,
           "name": "<시뮬레이션 이름>", "description": "..."}
    """

    def get(self, request, uid: str):
        diagram = _diagram(uid)
        if diagram is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        registration = (diagram.metadata or {}).get("fedit")
        remote: List[Dict[str, Any]] = []
        if registration and registration.get("fdt"):
            url = invoke_url(request, uid)
            try:
                remote = [s for s in brain.simulations(registration["fdt"])
                          if s.get("simulation_access_url") == url]
            except brain.BrainError as exc:
                return Response({"data": {"registration": registration, "remote": None, "error": str(exc)}})
        return Response({"data": {"registration": registration, "remote": remote,
                                  "invokeUrl": invoke_url(request, uid),
                                  "registerEnabled": fedit_register_enabled()}})

    def post(self, request, uid: str):
        if not fedit_register_enabled():
            # 연합트윈 공용 서버에 기록을 남기는 작업이라 기본으로 꺼 둔다.
            return Response({"error": "연합트윈 등록 기능이 꺼져 있습니다(서버 설정 SLCT_FEDIT_REGISTER=1 필요)."},
                            status=status.HTTP_403_FORBIDDEN)
        diagram = _diagram(uid)
        if diagram is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        body = request.data if isinstance(request.data, dict) else {}
        fdt = str(body.get("fdt") or "").strip()
        subjects = [str(s) for s in (body.get("subjects") or []) if str(s).strip()]
        if not fdt or not subjects:
            return Response({"error": "fdt 와 subjects(연합객체 id 목록)는 필수입니다."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            time_step = int(body.get("timeStep") or 1)
        except (TypeError, ValueError):
            return Response({"error": "timeStep 은 정수여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            interface = describe_interface(diagram.xml)
        except ModelError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        name = str(body.get("name") or diagram.title or f"SLCT 로직 {uid[:8]}")
        url = invoke_url(request, uid)
        payload = {
            "simulation_name": name,
            "description": str(body.get("description") or "서비스 로직 생성 도구에서 만든 로직"),
            "keywords": ["SLCT", "service-logic"],
            "creator_id": "SLCT",
            "simulation_subject": subjects,
            "simulation_access_url": url,
            "simulation_request_param": {n: "string" for n in interface["inputs"]} or None,
            "simulation_response_info": {n: "any" for n in interface["outputs"]} or None,
            "response_format_type": "json",
            "interface_type": "REST",
            "time_step": time_step,
            "resource_type": "federated_digital_object",
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            remote = brain.register_simulation(fdt, payload)
        except brain.BrainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        metadata = dict(diagram.metadata or {})
        metadata["fedit"] = {"fdt": fdt, "subjects": subjects, "timeStep": time_step,
                             "name": name, "invokeUrl": url, "response": remote}
        diagram.metadata = metadata
        diagram.save(update_fields=["metadata", "updated_at"])
        return Response({"data": metadata["fedit"]}, status=status.HTTP_201_CREATED)


class LogicDocsView(APIView):
    """로직 API 매뉴얼을 Swagger UI 로 보여준다(명세는 /spec 에서 자동 생성)."""

    def get(self, request, uid: str):
        from django.http import HttpResponse
        from django.utils.html import escape

        diagram = _diagram(uid)
        if diagram is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        title = escape(diagram.title or uid)
        spec_url = f"/api/logics/{escape(uid)}/spec"
        html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 서비스 로직 API</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
<style>body{{margin:0}} .topbar{{display:none}} header{{padding:14px 20px;background:#0f172a;color:#fff;font:600 15px system-ui}}
header a{{color:#93c5fd;font-weight:400;margin-left:12px}}</style></head>
<body><header>{title} — 서비스 로직 API <a href="/{escape(uid)}">편집기에서 보기</a></header>
<div id="ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({{url: "{spec_url}", dom_id: "#ui", deepLinking: true, tryItOutEnabled: true}});</script>
</body></html>"""
        return HttpResponse(html)
