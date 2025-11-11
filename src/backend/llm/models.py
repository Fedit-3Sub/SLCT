from django.db import models


class PromptTemplate(models.Model):
    name = models.CharField("이름", max_length=128, unique=True)
    template = models.TextField("템플릿", help_text="프롬프트 템플릿 본문")
    meta = models.JSONField("메타", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "프롬프트 템플릿"
        verbose_name_plural = "프롬프트 템플릿"

    def __str__(self) -> str:
        return self.name


class LlmConfig(models.Model):
    PROVIDER_CHOICES = [
        ("ollama", "Ollama"),
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("custom", "Custom"),
    ]

    name = models.CharField("이름", max_length=128, unique=True)
    provider = models.CharField("제공자", max_length=32, choices=PROVIDER_CHOICES, default="ollama")
    base_url = models.CharField("Base URL", max_length=255, blank=True, default="")
    api_key = models.CharField("API Key(옵션)", max_length=255, blank=True, default="", help_text="환경변수 사용 권장")
    model_name = models.CharField("모델명", max_length=128, blank=True, default="")
    is_default = models.BooleanField("기본값", default=False)
    enabled = models.BooleanField("활성화", default=True)
    meta = models.JSONField("메타", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "LLM 설정"
        verbose_name_plural = "LLM 설정"

    def __str__(self) -> str:
        return self.name


class LlmCallLog(models.Model):
    STATUS_CHOICES = [
        ("success", "성공"),
        ("error", "오류"),
    ]

    config = models.ForeignKey(LlmConfig, null=True, blank=True, on_delete=models.SET_NULL, related_name="call_logs")
    prompt = models.TextField("프롬프트")
    response = models.TextField("응답", blank=True, default="")
    tokens_in = models.IntegerField("입력 토큰", default=0)
    tokens_out = models.IntegerField("출력 토큰", default=0)
    cost = models.DecimalField("비용(USD)", max_digits=10, decimal_places=6, default=0)
    status = models.CharField("상태", max_length=16, choices=STATUS_CHOICES, default="success")
    error = models.TextField("오류", blank=True, default="")
    duration_ms = models.IntegerField("소요시간(ms)", default=0)
    request_meta = models.JSONField("요청 메타", default=dict, blank=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)

    class Meta:
        verbose_name = "LLM 호출 로그"
        verbose_name_plural = "LLM 호출 로그"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"LLM 호출({self.id}) - {self.status}"