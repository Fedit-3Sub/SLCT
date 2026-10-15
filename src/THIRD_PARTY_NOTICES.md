# 제3자 구성요소 고지 (Third-Party Notices)

서비스 로직 생성 도구(SLCT)는 GNU Lesser General Public License version 2.1(`LICENSE`)로
배포합니다. 이 문서는 SLCT 가 포함하거나 사용하는 외부 구성요소와 그 라이선스를 정리한
것입니다. 외부 구성요소는 SLCT 의 라이선스로 바뀌지 않고 각자의 원 라이선스를 따릅니다.

외부 구성요소는 배포 형태에 따라 두 가지로 나뉩니다.

- **A. 저장소에 소스가 포함된 것** — 배포물에 실물이 들어 있으므로 원 저작권 고지와
  허가 고지를 함께 배포합니다. 각 폴더의 `LICENSE` 파일 또는 파일 머리 주석에 원문이 있습니다.
- **B. 설치할 때 내려받는 것** — pnpm·pip 가 각 패키지 저장소에서 따로 내려받으며,
  이 저장소에는 들어 있지 않습니다.

확인 방법: ScanCode Toolkit 32.5.0 으로 이 디렉터리 전체를 스캔했습니다. 라이선스 머리말
없이 복사된 파일은 npm 에 공개된 원본 패키지와 파일 단위로 대조해 출처와 버전을 확인했습니다.
(기준일 2026-10-15)

---

## A. 저장소에 포함된 외부 소스

경로는 이 파일이 있는 디렉터리 기준입니다.

| 위치 | 원본 | 버전 | 라이선스 | 저작권자 | 비고 |
|---|---|---|---|---|---|
| `frontend/src/lib/bpmn-js/` | [bpmn-js](https://github.com/bpmn-io/bpmn-js) | 17.9.1 | bpmn.io License | Camunda Services GmbH | 일부 수정, 시뮬레이션 메뉴 추가 |
| `frontend/src/lib/bpmn-js-token-simulation/` | [bpmn-js-token-simulation](https://github.com/bpmn-io/bpmn-js-token-simulation) | 0.34.2 | MIT | Camunda Services GmbH | 일부 수정, 아이콘을 SVG 파일로 분리 |
| `frontend/src/lib/bpmn-js-token-simulation/icons/*.svg` (`pause-remove.svg` 제외 14개) | [Font Awesome Free](https://fontawesome.com) | 5.15.4 | CC BY 4.0 | Fonticons, Inc. | 위 패키지에 들어 있던 아이콘. 각 파일에 출처 주석 |
| `frontend/src/lib/bpmn-js-properties-panel/` | [bpmn-js-properties-panel](https://github.com/bpmn-io/bpmn-js-properties-panel) | 5.18.0 | MIT | camunda Services GmbH | Preact → React 로 옮기며 수정 |
| `frontend/src/lib/bpmn-properties-panel/` | [@bpmn-io/properties-panel](https://github.com/bpmn-io/properties-panel) | 3.22.0 | MIT | Camunda Services GmbH | Preact → React 로 옮기며 수정 |
| `frontend/src/lib/bpmn-js-color-picker/` | [bpmn-js-color-picker](https://github.com/bpmn-io/bpmn-js-color-picker) | 0.7.1 | MIT | Camunda Services GmbH | 수정 없음 |
| `frontend/src/lib/bpmn-js-add-exporter/` | [@bpmn-io/add-exporter](https://github.com/bpmn-io/add-exporter) | 0.2.0 | MIT | camunda Services GmbH | 수정 없음 |
| `frontend/public/font/`, `frontend/src/assets/css/bpmn.css`, `bpmn-codes.css`, `bpmn-embedded.css` | [bpmn-font](https://github.com/bpmn-io/bpmn-font) | 0.12.1 | SIL OFL 1.1 | Camunda Services GmbH | 수정 없음 |
| `frontend/src/assets/css/diagram-js.css` | [diagram-js](https://github.com/bpmn-io/diagram-js) | 14.8.0 | MIT | Camunda Services GmbH | 수정 없음 |
| `frontend/src/assets/css/bpmn-js.css` | bpmn-js | 17.9.1 | bpmn.io License | Camunda Services GmbH | 수정 없음 |
| `frontend/src/assets/css/properties-panel.css` | @bpmn-io/properties-panel | 3.22.0 | MIT | Camunda Services GmbH | 수정 없음 |
| `frontend/src/assets/css/bpmn-js-token-simulation.css` | bpmn-js-token-simulation | 0.34.2 | MIT | Camunda Services GmbH | 일부 수정 |
| `frontend/src/assets/css/color-picker.css` | bpmn-js-color-picker | 0.7.1 | MIT | Camunda Services GmbH | 수정 없음 |
| `frontend/` 프로젝트 골격 — 빌드·린트 설정, `src/main.ts`, `src/App.vue`, `src/router/`, `src/components/Navbar.vue`, `Hero.vue`, `Feature(s).vue`, `shared/`, `src/views/`, `src/assets/img/` | [vite-vue2-starter](https://github.com/lstoeferle/vite-vue2-starter) | 2021 | MIT | lstoeferle | 이 템플릿에서 시작해 수정 |

### bpmn.io License 준수 사항

bpmn-js 의 라이선스는 MIT 조건에 더해, 다이어그램에 표시되는 bpmn.io 워터마크를 지우거나
바꾸지 말고 화면에서 가리지 않을 것을 요구합니다. SLCT 는 워터마크를 그리는 코드
(`frontend/src/lib/bpmn-js/util/PoweredByUtil.js`, `BaseViewer.js` 의 `<project-logo>` 구간)를
원본 그대로 두며, 이를 숨기는 스타일도 쓰지 않습니다.

### 라이선스 원문 위치

| 라이선스 | 원문 |
|---|---|
| bpmn.io License | `frontend/src/lib/bpmn-js/LICENSE` |
| MIT (bpmn.io 패키지) | `frontend/src/lib/` 아래 각 폴더의 `LICENSE` |
| SIL OFL 1.1 | `frontend/public/font/LICENSE` |
| CC BY 4.0 | <https://creativecommons.org/licenses/by/4.0/> (아이콘 파일마다 출처 주석 포함) |
| MIT (vite-vue2-starter) | 아래 전문 |

```
MIT License

Copyright (c) 2021 lstoeferle

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## B. 설치할 때 내려받는 의존성

직접 의존성의 버전은 `frontend/pnpm-lock.yaml`, `backend/requirements.txt`,
`processor/requirements.txt` 에 고정돼 있습니다. Python 전이 의존성의 버전은 설치 시점에 따라
달라질 수 있으며, 아래 표는 2026-10-12 설치 결과입니다.

모든 의존성은 허용형 라이선스이며, `certifi` 만 파일 단위 카피레프트인 MPL-2.0 입니다.

### B-1. 프론트엔드 실행 의존성 (pnpm)

`pnpm build` 결과물(브라우저 번들)에 포함되는 패키지입니다.

| 패키지 | 버전 | 라이선스 |
|---|---|---|
| @babel/helper-string-parser | 7.23.4 | MIT |
| @babel/helper-validator-identifier | 7.22.20 | MIT |
| @babel/parser | 7.23.9 | MIT |
| @babel/types | 7.23.9 | MIT |
| @bpmn-io/cm-theme | 0.1.0-alpha.2 | MIT |
| @bpmn-io/diagram-js-ui | 0.2.3 | MIT |
| @bpmn-io/extract-process-variables | 0.8.0 | MIT |
| @bpmn-io/feel-editor | 1.6.1 | MIT |
| @bpmn-io/feel-lint | 1.2.0 | MIT |
| @codemirror/autocomplete | 6.17.0 | MIT |
| @codemirror/commands | 6.6.0 | MIT |
| @codemirror/language | 6.10.2 | MIT |
| @codemirror/lint | 6.8.1 | MIT |
| @codemirror/state | 6.4.1 | MIT |
| @codemirror/view | 6.28.4 | MIT |
| @lezer/common | 1.2.1 | MIT |
| @lezer/highlight | 1.2.0 | MIT |
| @lezer/lr | 1.4.1 | MIT |
| @lezer/markdown | 1.3.0 | MIT |
| @types/web-bluetooth | 0.0.16 | MIT |
| @vue/compiler-sfc | 2.7.16 | MIT |
| @vueuse/core | 9.13.0 | MIT |
| @vueuse/metadata | 9.13.0 | MIT |
| @vueuse/shared | 9.13.0 | MIT |
| array-move | 4.0.0 | MIT |
| asynckit | 0.4.0 | MIT |
| axios | 1.7.2 | MIT |
| bpmn-auto-layout | 1.3.0 | MIT |
| bpmn-moddle | 9.0.2 | MIT |
| bpmn-moddle | 10.0.0 | MIT |
| classnames | 2.5.1 | MIT |
| clsx | 2.1.1 | MIT |
| combined-stream | 1.0.8 | MIT |
| component-event | 0.2.1 | MIT |
| crelt | 1.0.6 | MIT |
| csstype | 3.1.3 | MIT |
| date-fns | 3.6.0 | MIT |
| delayed-stream | 1.0.0 | MIT |
| diagram-js | 14.8.0 | MIT |
| diagram-js-direct-editing | 3.0.1 | MIT |
| didi | 10.2.2 | MIT |
| domify | 1.4.2 | MIT |
| domify | 2.0.0 | MIT |
| feelers | 1.4.0 | MIT |
| feelin | 3.1.0 | MIT |
| focus-trap | 7.5.4 | MIT |
| follow-redirects | 1.15.6 | MIT |
| form-data | 4.0.0 | MIT |
| htm | 3.1.1 | Apache-2.0 |
| ids | 1.0.5 | MIT |
| inherits-browser | 0.1.0 | ISC |
| js-tokens | 4.0.0 | MIT |
| lang-feel | 2.1.1 | MIT |
| lezer-feel | 1.2.9 | MIT |
| loose-envify | 1.4.0 | MIT |
| luxon | 3.4.4 | MIT |
| mime-db | 1.52.0 | MIT |
| mime-types | 2.1.35 | MIT |
| min-dash | 4.2.1 | MIT |
| min-dash | 5.0.0 | MIT |
| min-dom | 4.2.1 | MIT |
| min-dom | 5.1.1 | MIT |
| moddle | 7.2.0 | MIT |
| moddle | 8.1.0 | MIT |
| moddle-xml | 11.0.0 | MIT |
| moddle-xml | 12.0.0 | MIT |
| nanoid | 3.3.7 | MIT |
| object-refs | 0.4.0 | MIT |
| path-intersection | 3.1.0 | MIT |
| picocolors | 1.0.0 | ISC |
| postcss | 8.4.35 | MIT |
| preact | 10.22.1 | MIT |
| prettier | 2.8.8 | MIT |
| proxy-from-env | 1.1.0 | MIT |
| querystringify | 2.2.0 | MIT |
| randomcolor | 0.6.2 | CC0 |
| react | 18.3.1 | MIT |
| react-dom | 18.3.1 | MIT |
| register-service-worker | 1.7.2 | MIT |
| requires-port | 1.0.0 | MIT |
| saxen | 10.0.0 | MIT |
| saxen | 11.0.2 | MIT |
| scheduler | 0.23.2 | MIT |
| source-map | 0.6.1 | BSD-3-Clause |
| source-map-js | 1.0.2 | BSD-3-Clause |
| style-mod | 4.1.2 | MIT |
| tabbable | 6.2.0 | MIT |
| tiny-svg | 3.1.2 | MIT |
| tiny-svg | 4.1.2 | MIT |
| to-fast-properties | 2.0.0 | MIT |
| url-parse | 1.5.10 | MIT |
| vue | 2.7.16 | MIT |
| vue-axios | 3.5.2 | MIT |
| vue-demi | 0.14.7 | MIT |
| vue-router | 3.6.5 | MIT |
| vuex | 3.6.2 | MIT |
| w3c-keyname | 2.2.8 | MIT |

개발 전용 의존성(빌드·린트 도구 409개)은 배포물에 포함되지 않습니다. 모두 허용형
라이선스(MIT, ISC, BSD-2/3-Clause, Apache-2.0, 0BSD, BlueOak-1.0.0, CC0-1.0, Python-2.0)이며,
데이터 패키지 `caniuse-lite`(CC BY 4.0)와 `spdx-exceptions`(CC BY 3.0)가 포함됩니다.

### B-2. 백엔드 (pip, `backend/requirements.txt`)

| 패키지 | 버전 | 라이선스 |
|---|---|---|
| Django | 5.0.6 | BSD-3-Clause |
| djangorestframework | 3.15.1 | BSD-3-Clause |
| django-cors-headers | 4.3.1 | MIT |
| drf-yasg | 1.21.7 | BSD-3-Clause |
| whitenoise | 6.7.0 | MIT |
| requests | 2.32.3 | Apache-2.0 |
| setuptools | 80.x (`<81`) | MIT |
| asgiref | 3.12.1 | BSD-3-Clause |
| sqlparse | 0.6.0 | BSD-3-Clause |
| inflection | 0.5.1 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pytz | 2026.5 | MIT |
| PyYAML | 6.0.3 | MIT |
| uritemplate | 4.2.0 | BSD-3-Clause OR Apache-2.0 |
| certifi | 2026.7.22 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| idna | 3.20 | BSD-3-Clause |
| urllib3 | 2.8.0 | MIT |

`certifi` 는 MPL-2.0 이며 수정 없이 사용합니다.

선택 설치(`backend/requirements-local-llm.txt`): `llama-cpp-python` 0.3.34 (MIT).
내장 LLM 모델 파일(Qwen2.5-1.5B-Instruct GGUF, Apache-2.0)은 저장소에 포함하지 않으며,
`backend/README.md` 의 안내대로 각 환경에서 내려받습니다.

### B-3. 프로세서 (pip, `processor/requirements.txt`)

| 패키지 | 버전 | 라이선스 |
|---|---|---|
| Flask | 3.1.3 | BSD-3-Clause |
| flask-cors | 6.0.5 | MIT |
| requests | 2.32.3 | Apache-2.0 |
| Werkzeug | 3.1.9 | BSD-3-Clause |
| Jinja2 | 3.1.6 | BSD-3-Clause |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| itsdangerous | 2.2.0 | BSD-3-Clause |
| click | 8.5.0 | BSD-3-Clause |
| blinker | 1.9.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| idna | 3.20 | BSD-3-Clause |
| urllib3 | 2.8.0 | MIT |

### B-4. 컨테이너 기반 이미지

| 이미지 | 용도 |
|---|---|
| `node:18-alpine` | 프론트엔드 빌드 단계에서만 사용 (배포 이미지에 남지 않음) |
| `nginx:1.27-alpine` | 프론트엔드 배포 이미지 |
| `python:3.11-slim` | 백엔드 배포 이미지 |
| `python:3.10-slim` | 프로세서 배포 이미지 |

각 이미지에 들어 있는 운영체제 패키지는 해당 이미지 배포처의 라이선스를 따릅니다.
