from django.contrib import admin
from .models import BpmnDiagram


@admin.register(BpmnDiagram)
class BpmnDiagramAdmin(admin.ModelAdmin):
    list_display = ("id", "uid", "title", "created_at", "updated_at")
    search_fields = ("uid", "title")
    list_filter = ("created_at",)
    ordering = ("-updated_at",)
