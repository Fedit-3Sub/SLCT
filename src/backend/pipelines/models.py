from django.db import models
from django.conf import settings


class Pipeline(models.Model):
    name = models.CharField("이름", max_length=128, unique=True)
    steps = models.JSONField("단계", default=list, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="소유자",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pipelines",
    )
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "파이프라인"
        verbose_name_plural = "파이프라인"

    def __str__(self) -> str:
        return self.name