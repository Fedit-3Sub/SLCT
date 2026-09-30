"""예제 서비스 로직을 다이어그램으로 등록한다.

    python manage.py load_samples            # 없는 것만 추가
    python manage.py load_samples --update   # 있으면 XML 을 예제로 덮어씀

편집기에서 http://{주소}/{uid} 로 열 수 있다(uid = 파일 이름).
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from bpmns.models import BpmnDiagram

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
TITLES = {
    "pohang-air-alert": "포항 대기질 경보 (연합트윈 실데이터)",
}


class Command(BaseCommand):
    help = "예제 서비스 로직을 등록한다."

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="이미 있으면 예제 XML 로 덮어쓴다")

    def handle(self, *args, update=False, **options):
        for path in sorted(SAMPLES_DIR.glob("*.bpmn")):
            uid = path.stem
            xml = path.read_text(encoding="utf-8")
            diagram = BpmnDiagram.objects.filter(uid=uid).first()
            if diagram and not update:
                self.stdout.write(f"건너뜀: {uid} (이미 있음)")
                continue
            if diagram:
                diagram.xml = xml
                diagram.title = TITLES.get(uid, diagram.title)
                diagram.save()
                self.stdout.write(f"갱신: {uid}")
            else:
                BpmnDiagram.objects.create(uid=uid, title=TITLES.get(uid, uid), xml=xml)
                self.stdout.write(f"추가: {uid}")
