# Dev Resource Hub — 통합 설계 및 비공개 저장소 경계

기준일: 2026-11-06  
상태: **PR 개발 및 검증 중**. 병합·실제 배포 상태는 GitHub Actions와 Pages에서 별도 확인합니다.

## 1. 검토 결과

| 저장소 | 접근 수준 | 역할 | 현재 통합 방법 |
| --- | --- | --- | --- |
| DevBlog | 공개 | 기업·기관 기술 문서 수집 및 검색 | 기존 검색과 허브 간 양방향 이동 |
| Design Atlas | 공개 | 100개 디자인, 42개 체험형 디자인 | 디자인 색인을 빌드 시 가져와 허브에서 검색·미리보기 링크 |
| Prompt Library | **비공개** | 76개 상황별 프롬프트 | 비공개 GitHub 원본 링크만 제공. 내용·제목·목록을 공개 사이트에 복사하지 않음 |
| DevKit | **비공개** | Claude Code 규칙·스킬·훅·검증 도구 | 통합하지 않음. 추후 개발 환경용 선택적 연결만 검토 |

핵심 결론: **공개 웹을 한 곳으로 묶되 비공개 저장소의 접근 권한을 절대로 완화하지 않습니다.**

원래 검토한 방식인 Prompt Library 전문을 DevBlog GitHub Pages로 가져오는 것은 비공개 데이터를 공개하는 문제가 있어 **폐기했습니다**. 실제 CI에서도 DevBlog의 GitHub Actions 토큰으로는 비공개 Prompt Library를 checkout할 수 없음이 확인되었습니다. 개인 액세스 토큰을 새로 넣거나 공개 권한을 변경하지 않습니다.

## 2. 사용자 흐름과 제공 기능

- 통합 진입점은 `public/hub.html`입니다.
- DevBlog에서 문제 해결 문서를 탐색합니다. 허브의 검색어를 `search.html?q=...`로 전달할 수 있습니다.
- 공개 Design Atlas의 100개 시안과 42개 체험형 디자인을 한 화면에서 검색하고 화면을 열어 볼 수 있습니다.
- Prompt Library는 비공개 GitHub 링크로 이동합니다. 권한이 없는 사용자에게는 GitHub에서 접근 불가로 표시되며, 사이트에서 이를 우회하지 않습니다.
- 각 원본 저장소와 수집 파이프라인은 변경하지 않습니다.

**한계:** 공개 허브 안에서 비공개 프롬프트를 검색·미리보기·복사하는 기능은 구현하지 않았습니다. 이를 추가하려면 인증된 비공개 앱 또는 사용자별 로컬 도구가 필요합니다. GitHub Pages는 개인별 자료 접근 제어를 대신하지 않습니다.

## 3. 기술 구성

- `scripts/build_resource_hub.py`: `_sources/design-atlas/docs/designs.json`만 읽어 `public/hub-data.json` 생성
- `public/hub-data.json`: 공개 디자인 시안·체험형 디자인만 수록. `schema: 2` 및 `source`, `counts`, `items[]`
- `public/hub.js`: 검색, 유형/세부 분야 필터, 결과 더 보기, URL 쿼리 상태, 기술 문서 검색 전달
- `public/hub.css`: 반응형, 색 대비, 키보드 포커스, 움직임 감소 지원
- `public/hub.html`: 공개 자료 탐색과 비공개 프롬프트 **외부 권한 검증 링크**
- `scripts/render.py`, `public/search.html`: 기존 사이트에서 허브로 이동 및 검색어 프리필
- `.github/workflows/collect.yml`과 `tests.yml`: 공개 Design Atlas만 sparse checkout 후 허브 색인 생성·검사
- `tests/test_resource_hub.py`: 유효성, 중복, 안전한 ID, 결정적 빌드, 비공개 데이터 배제 테스트

외부 공개 데이터를 새로 받아오지 못하면 빌드는 실패 상태를 기록하며, 기존 정적 색인 파일은 임시 파일 교체 방식으로 보존합니다. 현재 색인 파일은 공개 디자인 메타데이터만 포함합니다.

## 4. 왜 세 저장소를 한 레포로 합치지 않았나

- DevBlog는 Python RSS 배치, Design Atlas는 Node 정적 웹 빌드, Prompt Library는 Markdown 문서 아카이브로 역할이 구분됩니다.
- 모두 이동하면 링크·Git 히스토리·배포 설정·자동화가 불필요하게 바뀝니다.
- 무엇보다 Prompt Library를 공개 DevBlog 저장소로 합치는 것은 의도치 않은 데이터 공개를 초래할 수 있습니다.
- **공통 진입 화면 + 독립 원본** 구조가 현재 안전하고 유지관리가 간단합니다.

## 5. DevKit 별도 유지 결정

DevKit은 단순 자료가 아니라 Claude Code의 SessionStart/PreToolUse 훅, 안전 규칙, 개발 스킬, 평가를 실행하는 플러그인입니다.

- 콘텐츠 탐색 서비스와 실행 환경을 결합하면 배포 권한과 보안 경계가 뒤섞입니다.
- DevKit은 비공개 저장소와 독립 버전·CI를 유지합니다.
- 추후 선택형 연결을 할 수는 있습니다. 예: DevKit이 문제 진단 과정에서 DevBlog 검색 링크 또는 Design Atlas 시안을 **참고 자료로만** 제안.
- Prompt Library와 연결하더라도 사용자의 명시적 권한 범위 안에서만 동작해야 하며, 외부 프롬프트를 자동으로 명령 실행하지 않습니다.

## 6. 검증 및 릴리스 기준

### 자동 테스트

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --check public/hub.js
node --check /tmp/devblog-search.js  # search.html의 script를 추출한 뒤 검사
```

### 실제 공개 자료 생성

```bash
git clone --depth 1 https://github.com/lealle/design-atlas.git _sources/design-atlas
python scripts/build_resource_hub.py
python -c "import json; d=json.load(open('public/hub-data.json',encoding='utf-8')); assert d['schema']==2 and d['counts']['designs']==100 and d['counts']['experiences']==42; assert all(x['kind']!='prompt' for x in d['items'])"
python -m http.server 8000 --directory public
```

브라우저에서 `http://localhost:8000/hub.html`을 열고 검색, 필터, 실제 시안 링크, 모바일/키보드 조작, 검색어 전달, 비공개 저장소 접근 시 GitHub 권한 검증을 확인합니다.

**완료 정의:** PR CI 통과, 병합, Pages 배포, 실제 외부 링크와 브라우저 동작 확인을 구분해 기록합니다. CI 성공만으로 Pages 실배포를 주장하지 않습니다.

## 7. 한계·후속 작업

1. DevBlog 수년치 색인을 허브에 중복 다운로드하지 않도록 현행 독립 검색 유지; 추후 연관 검색 개선.
2. 공개 디자인 메타데이터와 사이트 시안의 변경 시점을 비교하는 버전/깨진 링크 검증 도입.
3. 비공개 Prompt Library까지 한 화면에서 보고 싶다면 **비공개 로컬 앱 또는 인증된 별도 서비스** 설계를 먼저 결정. 공개 GitHub Pages로 전문을 전송하는 방법은 금지.
4. DevKit 연결은 플러그인 내 권한 범위·비신뢰 프롬프트 취급·검증 근거 확보 후 선택적으로 시험.
5. 실제 사용자 과업 측정(문서 발견, 시안 선택, 관련성, 모바일 지연)에 근거하여 레포 물리적 통합 필요성 재검토.

여기 적힌 후속 항목은 **계획**이며 이번 PR의 구현 완료 항목이 아닙니다.
