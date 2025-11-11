from django.contrib import admin
from .models import DigitalTwin, DigitalTwinSource, DigitalTwinCallLog


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(DigitalTwinSource)
class DigitalTwinSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "url", "enabled", "updated_at")
    search_fields = ("name", "category", "url")
    list_filter = ("category", "enabled")
    ordering = ("name",)


@admin.register(DigitalTwinCallLog)
class DigitalTwinCallLogAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "method", "status_code", "duration_ms", "created_at")
    search_fields = ("path", "error")
    list_filter = ("status_code", "source")
    ordering = ("-created_at",)
