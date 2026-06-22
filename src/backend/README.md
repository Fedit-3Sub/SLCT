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

응답은 모두 `{"data": ..., "meta": ...}` 형식을 유지하여 프런트엔드가 기존 axios 래퍼(ApiService)로 문제 없이 소비할 수 있습니다.

**다이어그램 (`bpmns`)**

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/bpmns` | 목록 조회. `filters[uid][$eq]=...` 쿼리 지원. Strapi 스타일 응답(`data`/`meta`). |
| POST | `/api/bpmns` | 생성. 본문 `{ "data": { "uid": "", "xml": "", "metadata": {...} } }`. `uid` 미지정 시 자동 생성. |
| GET | `/api/bpmns/:id` | 단일 다이어그램 조회. |
| PUT | `/api/bpmns/:id` | 부분 업데이트. 본문 `{ "data": { "xml": "...", "metadata": {...} } }`. |

**LLM 코파일럿 (`llm`)**

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/llm/configs` | 활성화된 LLM 설정 목록(기본값 우선 정렬). `api_key`는 응답에 노출하지 않음. |
| POST | `/api/llm/configs` | LLM 설정 생성(provider: `ollama`/`openai`/`anthropic`/`custom`). |
| PATCH | `/api/llm/configs/:id` | LLM 설정 부분 수정. |
| GET | `/api/llm/logs` | 최근 호출 로그(최대 200건). |
| POST | `/api/llm/copilot` | 다이어그램 생성. 본문 `{ "prompt", "diagramUid", "llmId" }` → `{ "message", "generatedXml", "nodeSummary", "logId" }`. *(현재 생성 로직은 스텁 — provider 분기 미구현)* |

**디지털 트윈 (`digitaltwins`)**

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/digitaltwins` | 활성화된 시뮬레이터 소스 목록(비어 있으면 데모 항목 반환). |
| GET | `/api/digitaltwins/logs` | 최근 호출 로그(최대 200건). |
| POST | `/api/digitaltwins/call` | 시뮬레이션 호출. 본문 `{ "sourceId" \| "url", "data" }` → `{ "ok", "logId" }`. *(현재 실제 외부 HTTP 호출 없이 로그만 기록)* |

**파이프라인 · 노드 카탈로그 (`pipelines`)**

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/feditscraper/json` | 기존 Strapi가 반환하던 정적 엔티티 데이터 그대로 제공. |
| GET/POST | `/api/pipelines/run` | 토큰 시뮬레이션 트리거(`?id=` 수신, 바디 에코). |
| GET | `/api/custom-nodes` | 외부 API 노드 카탈로그(`?q=` 부분검색). |
| GET | `/api/search` | 통합 검색. `?q=` 키워드, `?types=builtin,custom,digitaltwin` 필터. |

**문서 · 관리자**

| Path | 설명 |
|------|------|
| `/api/docs/` · `/api/redoc/` | Swagger / ReDoc API 문서(drf-yasg). |
| `/api/schema.json` | OpenAPI 스키마. |
| `/admin/` | Django 관리자. |

#### 향후 확장
- Django 앱 구조이므로 인증(JWT 등), 디지털트윈 연동, LLM 엔드포인트, 버전 관리 등 추가 기능을 모듈 단위로 확장하기 용이합니다.
- 필요한 경우 Django REST Framework, Celery 등을 도입해 비동기 작업(스크래핑 등)도 연계할 수 있습니다.
