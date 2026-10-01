from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from typing import List, Dict
from django.db.models import Q
from urllib.parse import urlencode

from digitaltwins import brain, catalog, fedit_client
from digitaltwins.models import DigitalTwinSource
from bpmns.models import BpmnDiagram

from . import mock, runner
from .engine import ModelError, parse
from .models import PipelineRun


class PipelineRunView(APIView):
    """카탈로그 모의 실행 경로(`/api/pipelines/run?id=...`).

    토큰 시뮬레이션과 로직 실행기가 호출한다. 식별자에 정의된 출력 이름대로
    모의 값을 채워 돌려준다(`_mock: true`).
    """

    def post(self, request):
        sim_id = request.query_params.get("id") or ""
        payload = request.data if isinstance(request.data, dict) else {}
        # 토큰 시뮬레이션은 {did, uid, object} 를 보내므로 입력값으로 보지 않는다.
        inputs = {} if "object" in payload else payload
        result = mock.outputs_for(sim_id, inputs)
        result.update({
            "message": f"Pipeline run triggered for id={sim_id}",
            "received": payload,
            "status": "accepted",
        })
        return Response({"data": result}, status=status.HTTP_200_OK)

    def get(self, request):
        sim_id = request.query_params.get("id") or ""
        inputs = {k: v for k, v in request.query_params.items() if k != "id"}
        result = mock.outputs_for(sim_id, inputs)
        result.update({"message": f"Pipeline run (GET) for id={sim_id}", "status": "ok"})
        return Response({"data": result})


class PipelineExecuteView(APIView):
    """서비스 로직을 서버에서 실행한다.

    본문
      - uid:    저장된 다이어그램 식별자 (xml 이 없으면 이 다이어그램을 실행)
      - xml:    실행할 BPMN XML (편집 중인 다이어그램을 저장 전에 실행할 때)
      - inputs: 실행 입력값 {이름: 값}
      - start:  시작 이벤트 id (생략하면 첫 프로세스의 시작 이벤트 전부)
      - wait:   true 면 실행이 끝날 때까지 기다렸다가 결과를 돌려준다
    """

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        uid = str(body.get("uid") or "").strip()
        xml = body.get("xml") or ""
        inputs = body.get("inputs") or {}
        start = str(body.get("start") or "").strip()
        wait = str(body.get("wait", "")).lower() in ("1", "true", "yes")

        if not isinstance(inputs, dict):
            return Response({"error": "inputs 는 객체여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        diagram = BpmnDiagram.objects.filter(uid=uid).first() if uid else None
        if not xml:
            if diagram is None:
                return Response({"error": "xml 또는 저장된 다이어그램의 uid 가 필요합니다."},
                                status=status.HTTP_400_BAD_REQUEST)
            xml = diagram.xml
        if not isinstance(xml, str):
            return Response({"error": "xml 은 문자열이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 실행 기록을 만들기 전에 다이어그램을 해석할 수 있는지 먼저 확인한다.
        try:
            parse(xml)
        except ModelError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        run = PipelineRun.objects.create(
            diagram=diagram, diagram_uid=uid, xml=xml, inputs=inputs, start=start[:128],
        )
        if wait:
            runner.execute(run)
            return Response({"data": runner.serialize_run(run)}, status=status.HTTP_200_OK)

        runner.execute_in_background(run.pk)
        return Response({"data": runner.serialize_run(run, with_steps=False)}, status=status.HTTP_202_ACCEPTED)


class PipelineRunListView(APIView):
    """실행 기록 목록. `diagram=<uid>` 로 다이어그램별 조회."""

    def get(self, request):
        qs = PipelineRun.objects.all()
        uid = request.query_params.get("diagram")
        if uid:
            qs = qs.filter(diagram_uid=uid)
        try:
            limit = max(1, min(int(request.query_params.get("limit", 20)), 200))
        except ValueError:
            limit = 20
        items = [runner.serialize_run(r, with_steps=False) for r in qs[:limit]]
        return Response({"data": items, "meta": {"count": len(items)}})


class PipelineRunDetailView(APIView):
    """실행 기록 하나와 단계별 입출력."""

    def get(self, request, pk: int):
        run = PipelineRun.objects.filter(pk=pk).first()
        if run is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": runner.serialize_run(run)})


# ---- Custom Nodes (External API Nodes) - Mocked Endpoints ----

class CustomNodesView(APIView):
    """
    Returns a mocked catalog of external/custom nodes.
    Supports optional query parameter `q` for simple substring search.
    """

    def _mock_catalog(self) -> List[Dict]:
        # 연합트윈 연계 서비스 카탈로그. 실제 연계 자료를 반영한 목록이며
        # digitaltwins.catalog 에서 관리한다.
        return catalog.service_entries()

    def get(self, request):
        q = (request.query_params.get("q") or "").strip().lower()
        data = self._mock_catalog()
        if q:
            def _match(item: Dict) -> bool:
                hay = f"{item['name']} {item['category']} {item['description']} {item['api_id']}".lower()
                return q in hay
            data = [x for x in data if _match(x)]
        # Group meta by category counts for convenience
        meta = {"count": len(data), "categories": {}}
        for x in data:
            meta["categories"].setdefault(x["category"], 0)
            meta["categories"][x["category"]] += 1
        return Response({"data": data, "meta": meta}, status=status.HTTP_200_OK)


class UnifiedSearchView(APIView):
    """
    Unified search across built-in BPMN nodes, custom API nodes, and digital twin simulations.
    Query params:
      - q: search keyword (optional)
      - types: comma-separated filters among [builtin, custom, digitaltwin]
    """

    def _builtin_nodes(self) -> List[Dict]:
        items = [
            {"id": "builtin_start", "label": "Start Event", "category": "기본 노드", "bpmn_type": "bpmn:StartEvent", "icon": "bpmn-icon-start-event-none", "description": "프로세스 시작"},
            {"id": "builtin_end", "label": "End Event", "category": "기본 노드", "bpmn_type": "bpmn:EndEvent", "icon": "bpmn-icon-end-event-none", "description": "프로세스 종료"},
            {"id": "builtin_task", "label": "Task", "category": "기본 노드", "bpmn_type": "bpmn:Task", "icon": "bpmn-icon-task", "description": "일반 작업"},
            {"id": "builtin_service", "label": "Service Task", "category": "기본 노드", "bpmn_type": "bpmn:ServiceTask", "icon": "bpmn-icon-service-task", "description": "시스템/서비스 작업"},
            {"id": "builtin_gateway_xor", "label": "Exclusive Gateway", "category": "기본 노드", "bpmn_type": "bpmn:ExclusiveGateway", "icon": "bpmn-icon-gateway-none", "description": "단일 분기"},
            {"id": "builtin_datastore", "label": "Data Store", "category": "기본 노드", "bpmn_type": "bpmn:DataStoreReference", "icon": "bpmn-icon-data-store", "description": "데이터 저장소"},
            {"id": "builtin_dataobject", "label": "Data Object", "category": "기본 노드", "bpmn_type": "bpmn:DataObjectReference", "icon": "bpmn-icon-data-object", "description": "데이터 객체"},
            {"id": "builtin_send", "label": "Send Task", "category": "기본 노드", "bpmn_type": "bpmn:SendTask", "icon": "bpmn-icon-send-task", "description": "메시지 전송"},
            {"id": "builtin_receive", "label": "Receive Task", "category": "기본 노드", "bpmn_type": "bpmn:ReceiveTask", "icon": "bpmn-icon-receive-task", "description": "메시지 수신"},
            {"id": "builtin_group", "label": "Group", "category": "기본 노드", "bpmn_type": "bpmn:Group", "icon": "bpmn-icon-group", "description": "시각적 그룹"},
        ]
        return items

    def _custom_nodes(self) -> List[Dict]:
        # Reuse CustomNodesView mock
        custom = CustomNodesView()._mock_catalog()
        # Normalize to unified format
        return [
            {
                "id": f"custom::{item['id']}",
                "label": item["name"],
                "category": item.get("category", "외부 API"),
                "bpmn_type": item.get("bpmn_type", "bpmn:Task"),
                "icon": item.get("icon", "bpmn-icon-task"),
                "description": item.get("description", ""),
                "payload": {
                    "api_id": item.get("api_id"),
                    "schema": item.get("schema", {}),
                    # 로직 실행기·토큰 시뮬레이션이 호출할 실행 경로와 입출력 규격
                    "url": item.get("url") or f"{mock.MOCK_PATH}?id={item.get('api_id')}",
                    "method": item.get("method", ""),
                    "inputs": item.get("schema", {}).get("inputs", []),
                    "outputs": item.get("schema", {}).get("outputs", []),
                },
            }
            for item in custom
        ]

    def _digital_twins(self) -> List[Dict]:
        qs = DigitalTwinSource.objects.filter(enabled=True).order_by("name")
        if qs.exists():
            qs_items = list(qs.values("id", "name", "category", "url", "meta"))
            origin = "model"
        else:
            # 내장 카탈로그에 2세부 메타데이터의 실행 가능한 시뮬레이션을 더한다(대체하지 않음).
            entries = catalog.simulation_entries()
            if fedit_client.is_configured():
                known = {e["name"] for e in entries}
                extra = [e for e in fedit_client.list_simulations() if e["name"] not in known]
                for offset, e in enumerate(extra, start=len(entries) + 1):
                    entries.append({**e, "id": offset, "meta": {**e.get("meta", {}), "description": "2세부 메타데이터에 등록된 시뮬레이션"}})
            origin = "catalog+fedit" if any(e.get("meta", {}).get("source") == "fedit" for e in entries) else "catalog"
            qs_items = entries

        out = []
        for item in qs_items:
            meta = item.get("meta") or {}
            twin = meta.get("twin") or ""
            description = meta.get("description") or "디지털 트윈 시뮬레이션 호출"
            out.append({
                "id": f"dt::{item['id']}",
                "label": item.get("name"),
                # 분류를 세분화해 팔레트/검색에서 도메인별로 묶이도록 한다.
                "category": f"디지털 트윈 · {item.get('category')}" if item.get("category") else "디지털 트윈",
                "bpmn_type": catalog.SIMULATION_TYPE,
                "icon": catalog.ICONS[catalog.SIMULATION_TYPE],
                "description": f"[{twin}] {description}" if twin else description,
                "payload": {
                    "url": item.get("url"),
                    "source": origin,
                    "twinId": meta.get("twinId", ""),
                    "provider": meta.get("provider", ""),
                    "method": meta.get("method", ""),
                    "inputs": meta.get("inputs", []),
                    "outputs": meta.get("outputs", []),
                },
            })
        return out

    def _fedit_objects(self) -> List[Dict]:
        """Digital Brain 연합객체를 실데이터 조회 노드로 내놓는다."""
        out = []
        for item in brain.object_catalog():
            query = urlencode({"fdt": item["fdt_id"], "fdo": item["fdo_id"]})
            out.append({
                "id": f"fedit::{item['fdt_id']}::{item['fdo_id']}",
                "label": f"{item['fdo_name']} 최신 데이터",
                "category": f"연합트윈 실데이터 · {item['fdt_name']}",
                "bpmn_type": "bpmn:ServiceTask",
                "icon": "bpmn-icon-service-task",
                "description": f"[{item['fdt_name']}] {item['fdo_name']} 연합객체의 최신 동기화 데이터 (최근 {item.get('rowtime') or '-'})",
                "payload": {
                    "url": f"/api/fedit/objects/latest?{query}",
                    "method": "GET",
                    "source": "fedit-brain",
                    "twinId": item["fdt_id"],
                    "provider": "연합트윈 Digital Brain",
                    "inputs": [],
                    "outputs": item["outputs"],
                },
            })
        if out:
            # 속성 하나의 추세가 필요할 때 쓰는 범용 시계열 노드
            out.append({
                "id": "fedit::series",
                "label": "연합객체 시계열 요약",
                "category": "연합트윈 실데이터 · 공통",
                "bpmn_type": "bpmn:ServiceTask",
                "icon": "bpmn-icon-service-task",
                "description": "연합객체 속성 하나의 최근 값 목록과 최솟값·최댓값·평균",
                "payload": {
                    "url": "/api/fedit/objects/series",
                    "method": "GET",
                    "source": "fedit-brain",
                    "provider": "연합트윈 Digital Brain",
                    "inputs": ["fdt", "fdo", "property", "count"],
                    "outputs": ["latest", "min", "max", "avg", "count"],
                },
            })
        return out

    def get(self, request):
        q = (request.query_params.get("q") or "").strip().lower()
        types = (request.query_params.get("types") or "").strip().lower()
        type_set = {t for t in types.split(",") if t} if types else {"builtin", "custom", "digitaltwin", "fedit"}

        data: List[Dict] = []
        if "builtin" in type_set:
            data.extend(self._builtin_nodes())
        if "custom" in type_set:
            data.extend(self._custom_nodes())
        if "fedit" in type_set:
            data.extend(self._fedit_objects())
        if "digitaltwin" in type_set:
            data.extend(self._digital_twins())

        if q:
            def _match(item: Dict) -> bool:
                hay = " ".join([
                    str(item.get("label", "")),
                    str(item.get("category", "")),
                    str(item.get("description", "")),
                    str(item.get("bpmn_type", "")),
                ]).lower()
                return q in hay
            data = [x for x in data if _match(x)]

        # Meta grouping counts by category
        meta = {"count": len(data), "categories": {}}
        for x in data:
            c = x.get("category", "기타")
            meta["categories"].setdefault(c, 0)
            meta["categories"][c] += 1

        return Response({"data": data, "meta": meta}, status=status.HTTP_200_OK)
