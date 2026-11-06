# Dev Resource Hub — 공개 3개 프로젝트 통합 설계 및 DevKit 분리 검토

기준일: 2026-11-06  
상태: **통합 기능 개발 브랜치 / PR 검증 대상**. 이 문서는 병합·배포 완료를 의미하지 않습니다.

## 1. 결론

**DevBlog + Design Atlas + Prompt Library를 하나의 탐색 경험으로 통합하되, 저장소와 데이터 수집 파이프라인은 분리 유지**합니다. 공통 진입점은 `devblog/public/hub.html`이며, 다음 두 공개 저장소의 자료를 빌드 시 읽어 정적 JSON으로 출판합니다.

| 프로젝트 | 현재 책임 | 통합되는 기능 | 원본 소유권 |
| --- | --- | --- | --- |
| DevBlog | 기업·기관 RSS 수집 및 수년치 문서 검색 | 키워드 연계 검색, 학습 경로 진입 | DevBlog에 그대로 |
| Design Atlas | 100개 정적 시안, 42개 체험, Notion 디자인 | 100개 시안/42개 체험 검색과 실제 화면 이동 | Design Atlas에 그대로 |
| Prompt Library | 상황별 한국어 중심 프롬프트 76개 | 카테고리/텍스트 검색, 원문 미리보기, 복사 | Prompt Library에 그대로 |
| DevKit | 비공개 Claude Code 플러그인, 규칙·스킬·guard·eval | 이번 통합에는 포함하지 않음 | DevKit에 그대로 |

### 왜 모노레포로 병합하지 않았나

- **제품 경계가 다릅니다.** DevBlog는 Python RSS 데이터 처리, Design Atlas는 Node 정적 UI 빌드, Prompt Library는 Markdown 아카이브입니다.
- 모노레포로 이동하면 GitHub Pages 경로, 기존 즐겨찾기, 독립 CI, Git 히스토리, 갱신 작업이 한꺼번에 변경됩니다.
- 웹상의 **탐색 입구만 결합**해도 한곳에서 필요한 자료를 찾는 목표를 먼저 충족할 수 있습니다.
- 향후 진짜 단일 앱으로 이전할지 여부는 사용 데이터, 검색 품질, 독립 배포 비용을 확인한 뒤 결정합니다.

## 2. 실제 사용자 흐름

1. `hub.html`에서 프롬프트와 디자인을 한 검색창으로 찾습니다.
2. 원하는 분야 및 자료 유형으로 필터링하거나, 프롬프트 본문을 열고 복사합니다.
3. 디자인을 선택하면 Design Atlas의 실제 정적 시안 또는 체험 페이지가 새 창으로 열립니다.
4. 같은 검색어로 기술 사례를 찾을 때 `search.html?q=...`로 이동합니다.
5. 원문 출처와 GitHub 저장소 링크를 계속 표시합니다.

**검색 한계:** 수년치 DevBlog 기사 색인을 허브가 다시 다운로드하지 않습니다. 블로그 자체 검색 페이지로 쿼리를 넘기며, 추후 통합 색인 구현 시 기존 검색 성능의 병목부터 측정해야 합니다.

## 3. 데이터 구조 및 동기화

- `scripts/build_resource_hub.py`가 `_sources/prompt-library/prompts/*/*.md`와 `_sources/design-atlas/docs/designs.json`을 읽습니다.
- 결과는 `public/hub-data.json`이며, `schema: 1`, `source`, `counts`, `items[]`를 담습니다.
- 각 item은 `id`, `kind`, `title`, `category`, `category_label`, `description`, `url`을 공통으로 가집니다. 프롬프트에는 `content`, 시안에는 `number`, `style` 등이 추가됩니다.
- GitHub Actions의 `collect.yml`은 **공개** 형제 저장소를 sparse checkout한 뒤 RSS 및 검색 인덱스와 함께 허브 색인을 빌드합니다.
- `tests.yml`은 동일 공개 소스에서 허브 데이터 생성, 데이터 개수, 브라우저 JS 구문, Python 단위 테스트를 검증합니다.
- Git 추적 외부 소스는 `_sources/`로 가져오며 `.gitignore`로 제외합니다.
- 출력 파일은 임시 파일을 거쳐 교체하므로 입력 오류 발생 시 기존 출력물은 그대로 남습니다. 다만 워크플로는 실패 상태로 보고하여 잘못된 신뢰를 방지합니다.
- JSON은 결정적 순서로 출력합니다. 새 자료가 없어도 매 빌드마다 변화하는 타임스탬프 필드는 넣지 않습니다.

## 4. 보안·성능·접근성

- 소스 Markdown은 브라우저에서 `textContent`로 표시하므로 HTML을 실행하지 않습니다.
- 외부 이동은 승인한 HTTPS GitHub/Pages 호스트로 제한합니다. 외부 링크에는 `noopener noreferrer`를 사용합니다.
- 공개 프롬프트만 복제하므로 **DevKit 비공개 소스나 개발 환경의 설정·훅은 노출되지 않습니다**.
- 정적 데이터만 읽으며 계정, 쿠키, 서버, 유료 API, 개인정보 저장소가 필요하지 않습니다.
- 검색은 24개씩 추가 출력하여 초기 DOM 노드 수를 제한합니다. 색인은 현재 클라이언트 측 전체 다운로드이므로 규모 확대 시 분할/검색 엔진 교체가 필요합니다.
- 검색·필터·복사·닫기 기능은 키보드로 조작 가능하며 포커스 스타일, 상태 알림, 모바일 레이아웃, 움직임 감소를 지원합니다.
- Design Atlas의 기존 로컬 즐겨찾기는 브라우저·출처(origin)가 달라 자동 공유할 수 없습니다. 이를 허위로 약속하지 않습니다.

## 5. DevKit 검토 — **별도 유지, 선택적으로 연결**

DevKit은 `SessionStart`, `PreToolUse`, 스킬, 검증과 평가를 제공하는 **실행 가능한 개발 플러그인**입니다. 이를 공개 콘텐츠 허브와 직접 섞으면 배포 권한, 보안 경계, 업데이트 책임이 혼란스러워집니다.

**추천 경계**

- DevKit → DevBlog: 조사 단계에서 검증 가능한 자료를 찾아볼 수 있는 검색 링크만 제공(선택적).
- DevKit → Prompt Library: 개발자가 명시적으로 요청할 때 기존 프롬프트를 참고 문서로 추천(자동 실행 금지).
- DevKit → Design Atlas: UI 설계 과업에서 디자인 시안을 참고 자료로 연결(프로젝트 코드에 자동 적용 금지).
- DevKit 자체 저장소 및 평가 로그는 독립 운영하며 공개 허브로 복사하지 않습니다.

**향후 재검토 조건:** 안정적인 검색 API, 소스 라이선스/권한 검증, 비신뢰 콘텐츠를 프롬프트 명령으로 실행하지 않는 안전 경계, 독립 CI 성적이 확보되면 **연결 플러그인 형태**로 실험할 수 있습니다. 저장소를 물리적으로 합칠 필요는 없습니다.

## 6. 검증 방법과 릴리스 게이트

### 단위/구문 테스트

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --check public/hub.js
```

### 실제 원본을 이용한 색인 생성

```bash
git clone --depth 1 https://github.com/lealle/prompt-library.git _sources/prompt-library
git clone --depth 1 https://github.com/lealle/design-atlas.git _sources/design-atlas
python scripts/build_resource_hub.py
python -c "import json; d=json.load(open('public/hub-data.json',encoding='utf-8')); assert d['counts']['prompts'] > 0; assert d['counts']['designs'] == 100; assert d['counts']['experiences'] == 42"
python -m http.server --directory public 8000
```

브라우저 `http://localhost:8000/hub.html`에서 검색, 유형·카테고리 필터, 복사, GitHub 출처, 디자인 미리보기, 모바일/키보드 탐색과 검색어 전달을 확인합니다.

**병합 전 필수:** PR CI 녹색 및 정적 페이지 데이터 파일 생성 확인. **배포 후 별도:** 실제 Pages URL HTTP 200, 색인 로드, 검색어 프리필, 다른 저장소 링크, 모바일 확인. 자동화가 성공했다는 사실만으로 브라우저 배포를 확인한 것으로 간주하지 않습니다.

### 장애 및 롤백

- 외부 리포지토리 checkout/파싱 실패: 워크플로 실패로 알리고 배포·데이터 교체를 진행하지 않습니다.
- 허브 색인만 손상: 이전 정상 `hub-data.json`으로 되돌리거나 허브 링크를 임시로 숨깁니다. DevBlog RSS 수집 및 검색은 독립적으로 유지합니다.
- 전체 디자인/프롬프트 통합이 불필요해짐: `hub.html` 링크와 관련 허브 빌드 단계만 되돌리면 됩니다. 원본 세 저장소의 코드/데이터를 수정하지 않았습니다.

## 7. 후속 개선(이번 PR의 완료 범위 아님)

1. **R1 검색 의미 품질**: 기술 동의어, 카테고리 오분류/중복 측정, 자주 쓰는 검색 품질 평가.
2. **R2 더 강한 연결**: 기술 문서 ↔ 관련 프롬프트 ↔ 화면 시안 사이에 근거 있는 추천 규칙 수립.
3. **R3 색인 최적화**: 본문 로딩 분리, 분할 인덱스, 모바일 성능 예산 설정.
4. **R4 콘텐츠 버전 고정**: Git SHA provenance·업데이트 시각·깨진 링크 확인 및 실패 알림 추가.
5. **R5 디자인 적용 실험**: 단순 시안 보기에서 선택한 디자인 토큰의 프로젝트 적용 가이드를 제공(자동 수정은 별도 승인).
6. **R6 DevKit 연결 검증**: 현업 문제 진단 중 자료 추천 성공률과 오추천 위험 평가. 도구 실행과 자료 소비는 계속 분리.

위 항목은 계획이며 이번 작업의 구현·검증 완료 주장에 포함되지 않습니다.
