from rest_framework import serializers
from .models import DigitalTwinSource, DigitalTwinCallLog


class DigitalTwinSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwinSource
        fields = [
            "id",
            "name",
            "category",
            "url",
            "enabled",
            "meta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DigitalTwinCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwinCallLog
        fields = [
            "id",
            "source",
            "method",
            "path",
            "request_body",
            "response_body",
            "status_code",
            "duration_ms",
            "error",
            "created_at",
        ]
        read_only_fields = fields
