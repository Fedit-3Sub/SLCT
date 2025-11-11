from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from typing import List, Dict
from django.db.models import Q
from digitaltwins.models import DigitalTwinSource


class FedItScraperJsonView(APIView):
    def get(self, request):
        # Minimal stubbed dataset; adjust as needed
        data = [
            {
                "id": "entity_1",
                "title": "샘플 엔티티 1",
                "description": "데모 용도의 엔티티",
                "type": "demo",
                "reference": "https://example.com/ref/1",
            },
            {
                "id": "entity_2",
                "title": "샘플 엔티티 2",
                "description": "데모 용도의 엔티티",
                "type": "demo",
                "reference": "https://example.com/ref/2",
            },
        ]
        return Response({"data": data})


class PipelineRunView(APIView):
    def post(self, request):
        # Accept simulation trigger from the diagram token simulation
        sim_id = request.query_params.get("id")
        payload = request.data or {}
        # Echo back minimal result
        result = {
            "message": f"Pipeline run triggered for id={sim_id}",
            "received": payload,
            "status": "accepted",
        }
        return Response({"data": result}, status=status.HTTP_200_OK)

    def get(self, request):
        # Optional GET handler for testing
        sim_id = request.query_params.get("id")
        result = {
            "message": f"Pipeline run (GET) for id={sim_id}",
            "status": "ok",
        }
        return Response({"data": result})


# ---- Custom Nodes (External API Nodes) - Mocked Endpoints ----

class CustomNodesView(APIView):
    """
    Returns a mocked catalog of external/custom nodes.
    Supports optional query parameter `q` for simple substring search.
    """

    def _mock_catalog(self) -> List[Dict]:
        return [
            {
                "id": "custom_1",
                "name": "날씨 조회",
                "category": "외부 API",
                "api_id": "weather.current",
                "description": "현재 기상 정보를 조회하는 외부 API 노드",
                "schema": {"inputs": ["location"], "outputs": ["temperature", "humidity"]},
                "bpmn_type": "bpmn:ServiceTask",
                "icon": "bpmn-icon-service-task",
            },
            {
                "id": "custom_2",
                "name": "교통 혼잡도 분석",
                "category": "분석",
                "api_id": "traffic.analyze",
                "description": "교통 데이터를 수집하고 혼잡도를 산출",
                "schema": {"inputs": ["area"], "outputs": ["congestion_index"]},
                "bpmn_type": "bpmn:Task",
                "icon": "bpmn-icon-task",
            },
            {
                "id": "custom_3",
                "name": "SMS 알림 발송",
                "category": "알림",
                "api_id": "notify.sms",
                "description": "문자 메시지로 긴급 알림을 전송",
                "schema": {"inputs": ["phone", "message"], "outputs": ["status"]},
                "bpmn_type": "bpmn:SendTask",
                "icon": "bpmn-icon-send-task",
            },
        ]

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
                "payload": {"api_id": item.get("api_id"), "schema": item.get("schema", {})},
            }
            for item in custom
        ]

    def _digital_twins(self) -> List[Dict]:
        qs = DigitalTwinSource.objects.filter(enabled=True).order_by("name")
        if not qs.exists():
            # Align with DigitalTwinListView's demo items
            fallback = [
                {"id": 1, "name": "샘플 시뮬레이션 A", "category": "demo", "url": "/api/pipelines/run?id=simA"},
                {"id": 2, "name": "샘플 시뮬레이션 B", "category": "demo", "url": "/api/pipelines/run?id=simB"},
            ]
            qs_items = fallback
            from_model = False
        else:
            qs_items = list(qs.values("id", "name", "category", "url"))
            from_model = True
        out = []
        for item in qs_items:
            out.append({
                "id": f"dt::{item['id']}",
                "label": item.get("name"),
                "category": "디지털 트윈",
                "bpmn_type": "bpmn:ServiceTask",
                "icon": "bpmn-icon-service-task",
                "description": "디지털 트윈 시뮬레이션 호출",
                "payload": {"url": item.get("url"), "source": "model" if from_model else "demo"},
            })
        return out

    def get(self, request):
        q = (request.query_params.get("q") or "").strip().lower()
        types = (request.query_params.get("types") or "").strip().lower()
        type_set = {t for t in types.split(",") if t} if types else {"builtin", "custom", "digitaltwin"}

        data: List[Dict] = []
        if "builtin" in type_set:
            data.extend(self._builtin_nodes())
        if "custom" in type_set:
            data.extend(self._custom_nodes())
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
