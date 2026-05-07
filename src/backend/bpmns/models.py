from django.db import models
import uuid


class BpmnDiagram(models.Model):
    """BPMN 다이어그램 저장 모델

    - uid: 프런트/외부에서 참조할 수 있는 짧은 식별자 (고유)
    - title: 다이어그램 이름 (선택)
    - xml: BPMN XML 원문
    - metadata: 추가 메타데이터(JSON)
    - created_at/updated_at: 생성 및 수정 시간
    """

    uid = models.CharField("식별자", max_length=64, unique=True, blank=True, db_index=True)
    title = models.CharField("제목", max_length=255, blank=True, default="")
    xml = models.TextField("BPMN XML")
    metadata = models.JSONField("메타데이터", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "BPMN 다이어그램"
        verbose_name_plural = "BPMN 다이어그램"

    def save(self, *args, **kwargs):
        if not self.uid:
            self.uid = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        base = self.title or self.uid
        return f"BPMN: {base}"