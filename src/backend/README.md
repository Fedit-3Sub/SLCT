### core (Django)

이 프로젝트는 기존 프런트엔드가 기대하는 `/api/bpmns`와 `/api/feditscraper/json` 엔드포인트를 Strapi 없이 그대로 제공하기 위해 구성한 Django 서비스입니다.  
호출 경로와 요청/응답 구조를 Strapi와 동일하게 맞춰두었기 때문에, 프런트 코드 변경 없이 서버 주소만 새 인스턴스로 전환할 수 있습니다.

#### 준비
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate         # Windows라면 .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- 기본 DB는 `src/backend/db.sqlite3` (환경변수 `DJANGO_DB_PATH`로 경로 변경 가능)  
- 기본 포트는 `1337`이며 `python manage.py runserver 0.0.0.0:<port>`로 조정할 수 있습니다. 별도 인자를 주지 않으면 `0.0.0.0:1337`에서 시작합니다.

#### 엔드포인트 요약
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/bpmns` | `filters[uid][$eq]=...` 혹은 `filters[id][$eq]=...` 쿼리 지원. Strapi 스타일 응답. |
| POST | `/api/bpmns` | 본문 `{ "data": { "uid": "", "xml": "", "metadata": {...} } }` 구조. `uid` 미지정 시 자동 생성. |
| GET | `/api/bpmns/:id` | 단일 다이어그램 조회 (선택). |
| PUT | `/api/bpmns/:id` | 본문 `{ "data": { "xml": "...", "metadata": {...} } }` 구조로 업데이트. |
| GET | `/api/feditscraper/json` | 기존 Strapi가 반환하던 정적 데이터 그대로 제공. |

응답은 모두 `{"data": {...}, "meta": {...}}` 형식을 유지하여 프런트엔드가 기존 axios 래퍼(ApiService)로 문제 없이 소비할 수 있습니다.

#### 향후 확장
- Django 앱 구조이므로 인증(JWT 등), 디지털트윈 연동, LLM 엔드포인트, 버전 관리 등 추가 기능을 모듈 단위로 확장하기 용이합니다.
- 필요한 경우 Django REST Framework, Celery 등을 도입해 비동기 작업(스크래핑 등)도 연계할 수 있습니다.
