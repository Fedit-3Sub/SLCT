from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import catalog, fedit_client
from .models import DigitalTwinSource, DigitalTwinCallLog
from .serializers import DigitalTwinSourceSerializer, DigitalTwinCallLogSerializer
import time


def to_strapi_item(obj, attrs: dict):
    return {"id": obj.id, "attributes": attrs}


class DigitalTwinListView(APIView):
    def get(self, request):
        qs = DigitalTwinSource.objects.filter(enabled=True).order_by("name")
        if not qs.exists():
            # DB 가 비어 있으면 실제 연합트윈 메타데이터를 시도하고,
            # 토큰이 없거나 연결되지 않으면 내장 카탈로그로 대체한다.
            entries = fedit_client.list_simulations() if fedit_client.is_configured() else []
            origin = "fedit"
            if not entries:
                entries = catalog.simulation_entries()
                origin = "catalog"
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
