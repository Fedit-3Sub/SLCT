from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import brain, catalog, fedit_client
from .models import DigitalTwinSource, DigitalTwinCallLog
from .serializers import DigitalTwinSourceSerializer, DigitalTwinCallLogSerializer
import time


def to_strapi_item(obj, attrs: dict):
    return {"id": obj.id, "attributes": attrs}


class DigitalTwinListView(APIView):
    def get(self, request):
        qs = DigitalTwinSource.objects.filter(enabled=True).order_by("name")
        if not qs.exists():
            # 내장 카탈로그에 2세부 메타데이터의 실행 가능한 시뮬레이션을 더한다(대체하지 않음).
            entries = catalog.simulation_entries()
            if fedit_client.is_configured():
                known = {e["name"] for e in entries}
                extra = [e for e in fedit_client.list_simulations() if e["name"] not in known]
                for offset, e in enumerate(extra, start=len(entries) + 1):
                    entries.append({**e, "id": offset, "meta": {**e.get("meta", {}), "description": "2세부 메타데이터에 등록된 시뮬레이션"}})
            origin = "catalog+fedit" if any(e.get("meta", {}).get("source") == "fedit" for e in entries) else "catalog"
            items = [
                {
                    "id": entry["id"],
                    "attributes": {
                        "name": entry["name"],
                        "category": entry["category"],
                        "url": entry["url"],
                        "enabled": True,
                        **{k: v for k, v in entry.get("meta", {}).items() if k != "source"},
                    },
                }
                for entry in entries
            ]
            return Response({"data": items, "meta": {"source": origin, "count": len(items)}})
        items = [
            to_strapi_item(
                obj,
                {
                    "name": obj.name,
                    "category": obj.category,
                    "url": obj.url,
                    "enabled": obj.enabled,
                    "createdAt": obj.created_at.isoformat() if obj.created_at else None,
                    "updatedAt": obj.updated_at.isoformat() if obj.updated_at else None,
                },
            )
            for obj in qs
        ]
        return Response({"data": items, "meta": {}})


class DigitalTwinLogsView(APIView):
    def get(self, request):
        qs = DigitalTwinCallLog.objects.all().select_related("source").order_by("-created_at")[:200]
        items = []
        for log in qs:
            attrs = DigitalTwinCallLogSerializer(log).data
            items.append(to_strapi_item(log, attrs))
        return Response({"data": items, "meta": {"pagination": {"total": qs.count()}}})


class DigitalTwinCallView(APIView):
    def post(self, request):
        payload = request.data or {}
        source_id = payload.get("sourceId")
        endpoint = payload.get("url")
        body = payload.get("data", {})

        src = None
        if source_id:
            try:
                src = DigitalTwinSource.objects.get(pk=source_id)
                endpoint = src.url
            except DigitalTwinSource.DoesNotExist:
                pass
        if not endpoint:
            return Response({"error": "url or sourceId required"}, status=status.HTTP_400_BAD_REQUEST)

        # Simulate call and log it (no external HTTP for now)
        start = time.time()
        simulated_response = {"ok": True, "echo": body}
        duration_ms = int((time.time() - start) * 1000)
        log = DigitalTwinCallLog.objects.create(
            source=src,
            method="POST",
            path=endpoint,
            request_body=body,
            response_body=simulated_response,
            status_code=200,
            duration_ms=duration_ms,
        )
        return Response({"data": {"ok": True, "logId": log.id}})


# ---- 연합트윈 Digital Brain 실데이터 ----------------------------------------

class FeditObjectListView(APIView):
    """데이터가 들어오는 연합객체 목록과 각 객체의 측정값 이름."""

    def get(self, request):
        refresh = request.query_params.get("refresh") in ("1", "true")
        items = brain.object_catalog(refresh=refresh)
        return Response({"data": items, "meta": {"count": len(items), "brain": brain.base_url()}})


class FeditObjectLatestView(APIView):
    """연합객체 최신 데이터를 평평한 이름(`pm10`, `temp` …)으로 돌려준다."""

    def get(self, request):
        fdt = request.query_params.get("fdt", "").strip()
        fdo = request.query_params.get("fdo", "").strip()
        if not fdt or not fdo:
            return Response({"error": "fdt, fdo 는 필수입니다."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response({"data": brain.latest(fdt, fdo)})
        except brain.BrainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class FeditObjectSeriesView(APIView):
    """연합객체 속성 하나의 최근 값과 최솟값·최댓값·평균."""

    def get(self, request):
        fdt = request.query_params.get("fdt", "").strip()
        fdo = request.query_params.get("fdo", "").strip()
        prop = request.query_params.get("property", "").strip()
        if not fdt or not fdo or not prop:
            return Response({"error": "fdt, fdo, property 는 필수입니다."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = int(request.query_params.get("count", 24))
        except ValueError:
            count = 24
        try:
            return Response({"data": brain.series(fdt, fdo, prop, count)})
        except brain.BrainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class FeditMetadataView(APIView):
    """2세부 메타데이터 저장소의 단일 트윈 메타정보 요약(디지털 트윈·센서·제어기·시뮬레이션)."""

    def get(self, request):
        if not fedit_client.is_configured():
            return Response({"data": {}, "meta": {"configured": False}})
        data = {}
        for resource, label in fedit_client.RESOURCES.items():
            items = [fedit_client.summarize(x) for x in fedit_client.list_resource(resource)]
            data[resource] = {"label": label, "count": len(items), "items": items}
        return Response({"data": data, "meta": {"configured": True, "source": fedit_client.base_url()}})
