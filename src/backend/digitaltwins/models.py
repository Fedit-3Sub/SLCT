from django.db import models


class DigitalTwin(models.Model):
    name = models.CharField("이름", max_length=128, unique=True)
    description = models.TextField("설명", blank=True, default="")
    config = models.JSONField("설정", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "디지털 트윈"
        verbose_name_plural = "디지털 트윈"

    def __str__(self) -> str:
        return self.name


class DigitalTwinSource(models.Model):
    """외부 디지털 트윈/시뮬레이터 소스 정의

    - name: 표시 이름
    - category: 분류(예: demo, factory, traffic 등)
    - url: 프론트에서 호출할 엔드포인트(상대 또는 절대 경로)
    - enabled: 사용 여부
    - meta: 추가 메타
    """
    name = models.CharField("이름", max_length=128, unique=True)
    category = models.CharField("카테고리", max_length=64, blank=True, default="demo")
    url = models.CharField("엔드포인트 URL", max_length=255, help_text="상대(/api/...) 또는 절대 URL")
    enabled = models.BooleanField("활성화", default=True)
    meta = models.JSONField("메타", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "디지털 트윈 소스"
        verbose_name_plural = "디지털 트윈 소스"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class DigitalTwinCallLog(models.Model):
    source = models.ForeignKey(DigitalTwinSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="call_logs")
    method = models.CharField("메서드", max_length=8, default="POST")
    path = models.CharField("경로", max_length=255, blank=True, default="")
    request_body = models.JSONField("요청 바디", default=dict, blank=True)
    response_body = models.JSONField("응답 바디", default=dict, blank=True)
    status_code = models.IntegerField("상태코드", default=200)
    duration_ms = models.IntegerField("소요시간(ms)", default=0)
    error = models.TextField("오류", blank=True, default="")
    created_at = models.DateTimeField("생성일", auto_now_add=True)

    class Meta:
        verbose_name = "디지털 트윈 호출 로그"
        verbose_name_plural = "디지털 트윈 호출 로그"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        sid = self.source_id or "-"
        return f"DT 호출({self.id}) src={sid} status={self.status_code}"