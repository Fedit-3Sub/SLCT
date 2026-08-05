"""Ollama 서버에 적재된 모델을 LLM 설정으로 등록한다.

프런트엔드 코파일럿의 모델 선택 목록은 `LlmConfig` 를 그대로 노출한다.
이 명령으로 서버의 생성용 모델을 한 번에 등록해 두면 별도 입력 없이
드롭다운에서 고를 수 있다.

    python manage.py sync_ollama
    python manage.py sync_ollama --base-url http://192.168.0.10:11434
    python manage.py sync_ollama --prune   # 서버에 없는 항목은 비활성화
"""

from django.core.management.base import BaseCommand

from llm import ollama_client
from llm.models import LlmConfig


class Command(BaseCommand):
    help = "Ollama 서버의 생성용 모델을 LLM 설정으로 등록/갱신합니다."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="", help="Ollama 주소 (기본: http://localhost:11434)")
        parser.add_argument("--prune", action="store_true",
                            help="서버에 없는 ollama 설정을 비활성화")

    def handle(self, *args, **options):
        base_url = ollama_client.normalize_base_url(options.get("base_url"))

        if not ollama_client.is_reachable(base_url):
            self.stderr.write(self.style.ERROR(f"Ollama 서버에 연결할 수 없습니다: {base_url}"))
            return

        models = ollama_client.list_models(base_url)
        if not models:
            self.stdout.write(self.style.WARNING("등록할 생성용 모델이 없습니다(임베딩 전용 제외)."))
            return

        running = set(ollama_client.list_running(base_url))
        # 이미 적재된 모델이 응답이 빠르므로 기본값 후보로 우선한다.
        default_name = ollama_client.pick_model(base_url)
        seen = []

        for model in models:
            name = model["name"]
            seen.append(name)
            config, created = LlmConfig.objects.update_or_create(
                name=name,
                defaults={
                    "provider": "ollama",
                    "base_url": base_url,
                    "model_name": name,
                    "enabled": True,
                    "meta": {
                        "size": model.get("size", 0),
                        "family": model.get("family", ""),
                        "parameter_size": model.get("parameter_size", ""),
                        "loaded": name in running,
                    },
                },
            )
            mark = "신규" if created else "갱신"
            warm = " (적재됨)" if name in running else ""
            size_gb = (model.get("size") or 0) / 1e9
            self.stdout.write(f"  [{mark}] {name}  {size_gb:.1f}GB{warm}")

        if default_name:
            LlmConfig.objects.filter(is_default=True).exclude(name=default_name).update(is_default=False)
            LlmConfig.objects.filter(name=default_name).update(is_default=True)
            self.stdout.write(self.style.SUCCESS(f"기본 모델: {default_name}"))

        if options.get("prune"):
            stale = LlmConfig.objects.filter(provider="ollama").exclude(name__in=seen)
            count = stale.update(enabled=False)
            if count:
                self.stdout.write(self.style.WARNING(f"서버에 없는 설정 {count}건을 비활성화했습니다."))

        self.stdout.write(self.style.SUCCESS(f"총 {len(seen)}개 모델을 등록했습니다."))
