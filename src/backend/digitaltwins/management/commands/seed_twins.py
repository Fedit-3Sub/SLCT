"""연합트윈 시뮬레이터 카탈로그를 디지털트윈 소스로 등록한다.

등록해두면 노드 팔레트와 통합 검색이 DB 를 우선 사용하므로, 항목을 관리자
화면에서 수정하거나 비활성화할 수 있다.

    python manage.py seed_twins            # 내장 카탈로그로 등록
    python manage.py seed_twins --remote   # 연합트윈 메타데이터에서 가져와 등록
    python manage.py seed_twins --clear    # 기존 항목 삭제 후 등록

`--remote` 는 FEDIT_META_TOKEN 이 설정돼 있어야 하며, 조회에 실패하면
내장 카탈로그로 대체한다.
"""

from django.core.management.base import BaseCommand

from digitaltwins import catalog, fedit_client
from digitaltwins.models import DigitalTwinSource


class Command(BaseCommand):
    help = "연합트윈 시뮬레이터 목록을 디지털트윈 소스로 등록합니다."

    def add_arguments(self, parser):
        parser.add_argument("--remote", action="store_true",
                            help="연합트윈 메타데이터 API 에서 가져온다(토큰 필요)")
        parser.add_argument("--clear", action="store_true",
                            help="등록 전에 기존 소스를 모두 삭제한다")

    def handle(self, *args, **options):
        entries = []
        origin = "catalog"

        if options.get("remote"):
            if not fedit_client.is_configured():
                self.stderr.write(self.style.WARNING(
                    "FEDIT_META_TOKEN 이 설정되지 않아 원격 조회를 건너뜁니다."))
            else:
                entries = fedit_client.list_simulations()
                if entries:
                    origin = "fedit"
                else:
                    self.stderr.write(self.style.WARNING(
                        "원격 조회 결과가 없어 내장 카탈로그를 사용합니다."))

        if not entries:
            entries = catalog.simulation_entries()

        if options.get("clear"):
            deleted, _ = DigitalTwinSource.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"기존 소스 {deleted}건을 삭제했습니다."))

        created_count = updated_count = 0
        for entry in entries:
            meta = dict(entry.get("meta") or {})
            meta.setdefault("source", origin)
            _, created = DigitalTwinSource.objects.update_or_create(
                name=entry["name"][:128],
                defaults={
                    "category": (entry.get("category") or "")[:64],
                    "url": (entry.get("url") or "")[:255],
                    "enabled": True,
                    "meta": meta,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            mark = "신규" if created else "갱신"
            self.stdout.write(f"  [{mark}] {entry['name']}  ({entry.get('category', '-')})")

        self.stdout.write(self.style.SUCCESS(
            f"출처={origin} · 신규 {created_count}건 / 갱신 {updated_count}건"))
