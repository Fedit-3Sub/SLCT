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

#### AI 코파일럿 생성 엔진

`/api/llm/copilot` 은 아래 순서로 생성 엔진을 시도하며, 앞 단계를 쓸 수 없으면 다음으로 넘어갑니다.

| 순위 | 엔진 | 조건 | 특징 |
|---|---|---|---|
| 1 | 외부 LLM 서버 (Ollama) | 서버에 연결되는 경우 | 품질 최상, GPU 사용 시 빠름 |
| 2 | 내장 CPU LLM (llama.cpp) | 런타임 + 모델 파일이 있는 경우 | GPU 불필요, 응답 15~30초 |
| 3 | 규칙 기반 생성기 | 항상 | 의존성 없음, 즉시 응답 |

어느 경로를 타든 결과는 공통 빌더를 거치므로 **항상 유효한 BPMN XML** 이 반환됩니다.
좌표(BPMNDI)는 생성하지 않으며 프런트엔드가 자동 레이아웃으로 배치합니다.

**외부 LLM 서버(Ollama) 등록**

코파일럿 모델 선택 목록은 등록된 LLM 설정을 그대로 보여줍니다.
아래 명령으로 서버에 있는 생성용 모델을 한 번에 등록할 수 있습니다.

```bash
python manage.py sync_ollama                                  # 기본 http://localhost:11434
python manage.py sync_ollama --base-url http://<호스트>:11434
python manage.py sync_ollama --prune                          # 서버에 없는 항목 비활성화
```

- 임베딩 전용 모델은 자동으로 제외됩니다.
- 이미 메모리에 적재된(웜) 모델을 기본값으로 우선 선택합니다.
- 설정에 모델을 지정하지 않으면 요청 시점에 자동으로 고릅니다.
- 개별 등록/수정은 `POST /api/llm/configs`, `PATCH /api/llm/configs/:id` 또는 Django 관리자에서도 가능합니다.

> 모델이 메모리에 적재되지 않은 상태의 첫 요청은 적재 시간이 더해져 오래 걸립니다
> (실측: 8B 모델 콜드 약 150초 → 웜 약 5초). 제한시간은 `OLLAMA_TIMEOUT`(기본 180초)로 조정합니다.

**내장 CPU LLM 사용 (선택)**

설치하지 않아도 백엔드는 정상 동작하며, 이 경우 규칙 기반 생성기가 응답합니다.

```bash
# 1) 런타임 설치 (CPU 전용 사전 빌드 휠 — 컴파일 불필요)
pip install -r requirements-local-llm.txt \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# 2) 모델 내려받기 (약 1.1GB, Apache-2.0)
mkdir -p models
curl -L -o models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

모델 파일은 저장소에 포함하지 않습니다(`.gitignore` 처리).
`models/` 아래 `.gguf` 파일이 있으면 자동으로 인식합니다.

측정값 (Qwen2.5-1.5B Q4_K_M, Ryzen 7 5800X 8코어, GPU 미사용):

| 항목 | 값 |
|---|---|
| 최초 요청(모델 적재 포함) | 약 37초 |
| 이후 생성 | 17~42초 (평균 29초) |
| 처리량 | 약 16~18 tok/s |
| 메모리(RSS) | 약 2.0GB |

스레드를 2 → 8개로 늘려도 처리량은 15.8 → 18.0 tok/s 로 약 14% 만 개선됩니다.
연산보다 메모리 대역폭에 좌우되므로 **코어가 적은 서버에서도 성능이 크게 떨어지지 않습니다**.
컨테이너 메모리 제한은 2.5GB 이상을 권장합니다.

관련 환경변수:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OLLAMA_ENABLED` | `1` | `0` 이면 외부 LLM 서버를 건너뛴다. 서버가 떠 있어도 내장 CPU LLM 부터 사용하므로, 외부 서버가 없는 배포 환경을 그대로 재현할 때 쓴다 |
| `LOCAL_LLM_ENABLED` | `1` | `0` 이면 내장 LLM 을 건너뛰고 규칙 기반만 사용 |
| `LOCAL_LLM_MODEL_PATH` | (자동 탐색) | 특정 GGUF 파일 경로 지정 |
| `LOCAL_LLM_MODEL_DIR` | `src/backend/models` | 모델 탐색 디렉터리 |
| `LOCAL_LLM_THREADS` | 물리 코어 수 | 논리 코어 수만큼 늘리면 오히려 느려집니다 |
| `LOCAL_LLM_CTX` | `2048` | 컨텍스트 길이 |
| `LOCAL_LLM_MAX_TOKENS` | `768` | 최대 생성 토큰 |

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
