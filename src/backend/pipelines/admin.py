from django.contrib import admin
from .models import Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("created_at",)
    ordering = ("name",)
