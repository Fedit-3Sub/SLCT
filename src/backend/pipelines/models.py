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

class PipelineRun(models.Model):
    """서비스 로직(BPMN) 한 번의 서버 실행 기록."""

    STATUS_CHOICES = [
        ("pending", "대기"),
        ("running", "실행 중"),
        ("succeeded", "성공"),
        ("failed", "실패"),
    ]

    diagram = models.ForeignKey(
        "bpmns.BpmnDiagram",
        verbose_name="다이어그램",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    diagram_uid = models.CharField("다이어그램 식별자", max_length=64, blank=True, db_index=True)
    xml = models.TextField("실행한 BPMN XML")
    start = models.CharField("시작 이벤트", max_length=128, blank=True)
    trigger = models.CharField(
        "실행 경로", max_length=16, default="editor",
        help_text="editor: 편집기 실행, api: 로직 API 호출, fedit: 연합트윈 시뮬레이션 호출",
    )
    result = models.JSONField("결과", null=True, blank=True)
    status = models.CharField("상태", max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    inputs = models.JSONField("입력값", default=dict, blank=True)
    variables = models.JSONField("최종 값", default=dict, blank=True)
    error = models.TextField("오류", blank=True)
    created_at = models.DateTimeField("요청일", auto_now_add=True)
    started_at = models.DateTimeField("시작", null=True, blank=True)
    finished_at = models.DateTimeField("종료", null=True, blank=True)

    class Meta:
        verbose_name = "로직 실행"
        verbose_name_plural = "로직 실행"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.diagram_uid or '(임시)'} #{self.pk} {self.status}"


class PipelineStep(models.Model):
    """실행 중 노드 하나를 지난 기록(입출력 히스토리)."""

    run = models.ForeignKey(PipelineRun, verbose_name="실행", on_delete=models.CASCADE, related_name="steps")
    seq = models.PositiveIntegerField("순서")
    node_id = models.CharField("노드 id", max_length=128)
    node_type = models.CharField("노드 종류", max_length=64)
    node_name = models.CharField("노드 이름", max_length=255, blank=True)
    scope_id = models.CharField("범위", max_length=128, blank=True)
    status = models.CharField("상태", max_length=16)
    inputs = models.JSONField("입력", default=dict, blank=True)
    outputs = models.JSONField("출력", default=dict, blank=True)
    request = models.JSONField("요청", default=dict, blank=True)
    response = models.JSONField("응답", null=True, blank=True)
    flows = models.JSONField("나간 흐름", default=list, blank=True)
    warnings = models.JSONField("경고", default=list, blank=True)
    error = models.TextField("오류", blank=True)
    attempts = models.PositiveIntegerField("시도 횟수", default=0)
    started_at = models.DateTimeField("시작", null=True, blank=True)
    duration_ms = models.PositiveIntegerField("소요(ms)", default=0)

    class Meta:
        verbose_name = "실행 단계"
        verbose_name_plural = "실행 단계"
        ordering = ["run", "seq"]

    def __str__(self) -> str:
        return f"#{self.run_id}-{self.seq} {self.node_name or self.node_id}"
