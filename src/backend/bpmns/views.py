from typing import Any, Dict
from django.utils.dateformat import format as date_format
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import BpmnDiagram
from .serializers import BpmnDiagramSerializer


# Helpers to shape Strapi-like responses expected by the frontend

def to_strapi_attributes(instance: BpmnDiagram) -> Dict[str, Any]:
    return {
        "uid": instance.uid,
        "title": instance.title,
        "xml": instance.xml,
        "metadata": instance.metadata,
        "createdAt": instance.created_at.isoformat() if instance.created_at else None,
        "updatedAt": instance.updated_at.isoformat() if instance.updated_at else None,
    }


def to_strapi_item(instance: BpmnDiagram) -> Dict[str, Any]:
    return {"id": instance.id, "attributes": to_strapi_attributes(instance)}


class BpmnListCreateView(APIView):
    def get(self, request):
        # Support filter like filters[uid][$eq]=<uid>
        uid_eq = request.query_params.get("filters[uid][$eq]")
        qs = BpmnDiagram.objects.all()
        if uid_eq:
            qs = qs.filter(uid=uid_eq)
        items = [to_strapi_item(obj) for obj in qs.order_by("-updated_at")]
        meta = {"pagination": {"page": 1, "pageSize": len(items), "pageCount": 1, "total": len(items)}}
        return Response({"data": items, "meta": meta})

    def post(self, request):
        payload = request.data or {}
        data = payload.get("data") or payload  # accept both Strapi-style and plain
        serializer = BpmnDiagramSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            return Response({"data": to_strapi_item(instance)}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class BpmnRetrieveUpdateView(APIView):
    def get_object(self, pk: int) -> BpmnDiagram:
        return BpmnDiagram.objects.get(pk=pk)

    def get(self, request, pk: int):
        try:
            instance = self.get_object(pk)
        except BpmnDiagram.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": to_strapi_item(instance)})

    def put(self, request, pk: int):
        try:
            instance = self.get_object(pk)
        except BpmnDiagram.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        payload = request.data or {}
        data = payload.get("data") or payload
        serializer = BpmnDiagramSerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response({"data": to_strapi_item(instance)})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
