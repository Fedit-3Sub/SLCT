from rest_framework import serializers
from .models import LlmConfig, LlmCallLog


class LlmConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LlmConfig
        fields = [
            "id",
            "name",
            "provider",
            "base_url",
            "api_key",
            "model_name",
            "is_default",
            "enabled",
            "meta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            # API 키는 저장만 하고 응답에는 노출하지 않는다.
            "api_key": {"write_only": True, "required": False},
        }


class LlmCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LlmCallLog
        fields = [
            "id",
            "config",
            "prompt",
            "response",
            "tokens_in",
            "tokens_out",
            "cost",
            "status",
            "error",
            "duration_ms",
            "request_meta",
            "created_at",
        ]
        read_only_fields = fields
