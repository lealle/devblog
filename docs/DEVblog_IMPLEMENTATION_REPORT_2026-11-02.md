# DevBlog 개발 완료 보고서

- **작성 기준일:** 2026-11-02
- **대상 저장소:** [lealle/devblog](https://github.com/lealle/devblog)
- **대상 PR:** [#1 전체 문서 검색 및 일일 배포 기반 구축](https://github.com/lealle/devblog/pull/1)
- **범위:** RSS 수집 안정화, 전체 문서 검색, 기술 분류, 문제 해결 탐색, CI 및 정적 사이트 생성
- **완료 판정:** 기능 구현 및 PR CI 검증 완료. 실제 운영 배포와 브라우저 실사용 확인은 별도 확인 필요.

## 1. 개요

기존 DevBlog는 최근 8일 내 수집 글을 날짜별로 표시하며 화면에 노출된 문서만 문자열 검색할 수 있었다. 이번 변경은 기존 수집 데이터 형식을 유지하면서 **월별 JSONL 전체 아카이브 검색**과 기술 분류 및 문제 해결 경로 탐색을 추가한다.

## 2. 구현 내역

| 분야 | 변경 사항 | 구현 파일 |
| --- | --- | --- |
| 전체 검색 | 월별 JSONL 전체를 중복 제거해 JSON 색인 생성 | `scripts/build_search_index.py` |
| 검색 화면 | 제목·출처·요약 검색, 국내/해외 필터, 최신/관련도 정렬, 30건씩 더 보기 | `public/search.html` |
| 자동 분류 | Backend, Frontend, Database, Infrastructure, AI/ML, Security, Architecture, Engineering 다중 분류 | `scripts/classify_articles.py` |
| 문서 유형 | troubleshooting, comparison, tutorial, general 규칙 분류 | `scripts/classify_articles.py` |
| 문제 해결 탐색 | 원인 파악 → 해결 방법 → 대안 비교 → 실무 검증 단계별 검색 결과 추천 | `public/search.html` |
| 수집 안정화 | 3회 연속 실패한 RSS를 7일 후 재시도 | `scripts/collect.py` |
| 배포 흐름 | 매일 수집 이후 렌더링·색인 생성·Pages 배포하도록 변경 | `.github/workflows/collect.yml` |
| 검증 | Python 단위 테스트, JS 문법 검사, 빌드 스모크 테스트 | `.github/workflows/tests.yml` |
| 운영 문서 | 실행·한계·후속 과제 기록 | `docs/SEARCH_AND_DISCOVERY.md` |

## 3. 검증 결과

- **GitHub Actions tests run #7:** 성공 (`41333457605`).
- 확인된 성공 단계: 의존성 설치, Python 단위 테스트, JavaScript 문법 검사, 정적 빌드 스모크 테스트.
- PR #1은 최신 검사 시 병합 가능한 상태였다.
- **주의:** GitHub Actions 검증은 실제 사용자의 브라우저 클릭 테스트, 검색 결과 품질 측정, GitHub Pages 실배포 성공을 보증하지 않는다.

## 4. 아키텍처

```text
data/feeds.json
    ↓
scripts/collect.py
    ↓
data/articles/YYYY-MM.jsonl
    ├── scripts/render.py → public/index.html (최근 글)
    └── scripts/build_search_index.py
           └── scripts/classify_articles.py
                ↓
          public/search-index.json
                ↓
          public/search.html (전체 검색 + 문제 해결 경로)
```

정적 사이트 및 GitHub Pages 기반을 유지하여 서버·DB·외부 AI API 없이 동작하도록 구성했다.

## 5. 알려진 제약 및 위험

1. 검색 색인은 전체 JSON을 브라우저에 다운로드한다. 문서 수가 커지면 초기 로딩·메모리 비용이 증가한다. 색인 크기 측정 후 분할 색인 또는 Pagefind 검토가 필요하다.
2. 분류는 제목과 RSS 요약의 정규식 매칭이다. 정확도, 재현율, 추천 품질에 대한 정량 평가가 없다.
3. 문제 해결 경로는 검색 결과의 키워드·문서 유형에 따른 탐색 지원이다. 실제 기술적 정답 또는 검증된 해결 순서가 아니다.
4. RSS 본문을 직접 분석하지 않으므로 요약이 없거나 부정확한 문서는 누락될 수 있다.
5. URL 중복 판단은 기존 방식에 의존한다. 의미 있는 쿼리 매개변수를 가진 다른 글이 같은 것으로 인식될 가능성이 있다.
6. 예약된 GitHub Actions 실행은 지연되거나 누락될 수 있다.
7. 현재 원문 링크를 제공하며 원문 전체를 복제하지 않는다.
8. 실제 배포와 실사용 브라우저 검증은 운영 확인 항목으로 남는다.

## 6. 후속 개선 우선순위

| 우선순위 | 과제 | 완료 기준 |
| --- | --- | --- |
| P0 | 운영 Pages 배포 확인 | 배포 워크플로 성공 및 검색 화면·색인 접근 확인 |
| P1 | 검색 색인 용량 및 속도 평가 | 문서 수별 JSON 크기·초기 검색 시간 측정 |
| P1 | 추천 평가 데이터셋 | 대표 검색어별 기대 문서 및 오분류 사례 수집 |
| P1 | RSS URL 정규화 개선 | 기존 해시와 호환되는 마이그레이션·회귀 테스트 |
| P2 | 기술 동의어·공식 문서 연결 | 근거 링크와 추천 이유 표시 |
| P2 | 관계 기반 문서 추천 | 선행 개념·심화·비교 관계를 명시적으로 연결 |
| P3 | 개인화 | 이용자 선택에 따른 즐겨찾기·읽기 상태 (개인정보/저장 방식 검토 후) |

## 7. 변경 및 배포 관리

- 기존 데이터 파일 삭제 없음.
- 외부 서비스/API 유료 결제 기능 추가 없음.
- 구현은 PR #1에 기록되며, 병합/운영 배포 상태는 GitHub PR 및 Actions 기록을 기준으로 판단한다.
- 이 보고서는 확인된 구현과 CI 결과를 기록하며 미검증 사항을 완료로 표현하지 않는다.
