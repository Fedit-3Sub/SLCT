from django.contrib import admin
from .models import PromptTemplate, LlmConfig, LlmCallLog


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(LlmConfig)
class LlmConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "provider", "model_name", "is_default", "enabled", "updated_at")
    search_fields = ("name", "model_name", "provider")
    list_filter = ("provider", "is_default", "enabled")
    ordering = ("name",)


@admin.register(LlmCallLog)
class LlmCallLogAdmin(admin.ModelAdmin):
    list_display = ("id", "config", "status", "tokens_in", "tokens_out", "duration_ms", "created_at")
    search_fields = ("prompt", "response", "error")
    list_filter = ("status", "config")
    ordering = ("-created_at",)
