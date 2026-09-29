from django.contrib import admin
from .models import Pipeline, PipelineRun, PipelineStep


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("created_at",)
    ordering = ("name",)


class PipelineStepInline(admin.TabularInline):
    model = PipelineStep
    extra = 0
    fields = ("seq", "node_name", "node_type", "status", "inputs", "outputs", "error", "duration_ms")
    readonly_fields = fields
    can_delete = False


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ("id", "diagram_uid", "status", "created_at", "finished_at")
    list_filter = ("status", "created_at")
    search_fields = ("diagram_uid", "error")
    readonly_fields = ("created_at", "started_at", "finished_at")
    inlines = [PipelineStepInline]
