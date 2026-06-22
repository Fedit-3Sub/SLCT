from rest_framework import serializers
from .models import BpmnDiagram


class BpmnDiagramSerializer(serializers.ModelSerializer):
    class Meta:
        model = BpmnDiagram
        fields = ["uid", "title", "xml", "metadata"]
        extra_kwargs = {
            # uid는 비어 있으면 모델 save()에서 자동 생성된다.
            "uid": {"required": False},
            "title": {"required": False},
            "metadata": {"required": False},
        }
