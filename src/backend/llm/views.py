from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import LlmConfig, LlmCallLog
from .serializers import LlmConfigSerializer, LlmCallLogSerializer
from .services import generate_with_llm


def to_strapi_item(obj, attrs: dict):
    return {"id": obj.id, "attributes": attrs}


class LlmConfigsView(APIView):
    def get(self, request):
        qs = LlmConfig.objects.filter(enabled=True).order_by("-is_default", "name")
        items = [
            to_strapi_item(
                obj,
                {
                    "name": obj.name,
                    "provider": obj.provider,
                    "base_url": obj.base_url,
                    "model_name": obj.model_name,
                    "isDefault": obj.is_default,
                    "enabled": obj.enabled,
                    "createdAt": obj.created_at.isoformat() if obj.created_at else None,
                    "updatedAt": obj.updated_at.isoformat() if obj.updated_at else None,
                },
            )
            for obj in qs
        ]
        return Response({"data": items, "meta": {}})

    def post(self, request):
        serializer = LlmConfigSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response({"data": to_strapi_item(obj, serializer.data)}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class LlmConfigDetailView(APIView):
    def patch(self, request, pk: int):
        obj = get_object_or_404(LlmConfig, pk=pk)
        serializer = LlmConfigSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            obj = serializer.save()
            return Response({"data": to_strapi_item(obj, serializer.data)})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class LlmLogsView(APIView):
    def get(self, request):
        qs = LlmCallLog.objects.all().select_related("config").order_by("-created_at")[:200]
        items = []
        for log in qs:
            attrs = LlmCallLogSerializer(log).data
            items.append(to_strapi_item(log, attrs))
        return Response({"data": items, "meta": {"pagination": {"total": qs.count()}}})


class LlmCopilotView(APIView):
    def post(self, request):
        payload = request.data or {}
        prompt = payload.get("prompt", "").strip()
        diagram_uid = payload.get("diagramUid") or ""
        llm_id = payload.get("llmId")
        if not prompt:
            return Response({"error": "prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

        # resolve config
        config = None
        if llm_id:
            config = LlmConfig.objects.filter(id=llm_id, enabled=True).first()
        if not config:
            config = LlmConfig.objects.filter(is_default=True, enabled=True).first() or LlmConfig.objects.filter(enabled=True).first()

        # call provider (stubbed service) and log
        result = generate_with_llm(prompt=prompt, config=config, diagram_uid=diagram_uid)
        log = LlmCallLog.objects.create(
            config=config,
            prompt=prompt,
            response=result.get("generatedXml") or result.get("message", ""),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
            cost=result.get("cost", 0) or 0,
            status="success" if not result.get("error") else "error",
            error=result.get("error", ""),
            duration_ms=result.get("duration_ms", 0),
            request_meta={"diagram_uid": diagram_uid},
        )

        data = {
            "message": result.get("message") or f"요청하신 요구사항을 바탕으로 기본 시작 이벤트를 포함한 다이어그램 초안을 생성했습니다. (uid={diagram_uid})",
            "generatedXml": result.get("generatedXml"),
            "nodeSummary": result.get("nodeSummary") or "- StartEvent 하나로 시작하는 간단한 프로세스",
            "logId": log.id,
        }
        return Response({"data": data})
