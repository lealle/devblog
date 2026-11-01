# DevBlog 전체 검색과 문제 해결 경로

## 구성

- `scripts/build_search_index.py`: `data/articles/YYYY-MM.jsonl` 전체를 읽어 `public/search-index.json` 생성
- `scripts/classify_articles.py`: 제목과 RSS 요약에서 기술 분야와 문서 유형을 규칙 기반으로 분류
- `public/search.html`: 검색, 지역/기술 필터, 정렬, 문제 해결 경로 표시
- `scripts/collect.py`: 연속 실패한 RSS를 7일 간격으로 재시도
- `.github/workflows/tests.yml`: 단위 테스트, JavaScript 문법, 정적 사이트 생성 검사

## 로컬 검증

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
python scripts/render.py
python scripts/build_search_index.py
python -m http.server 8000 --directory public
```

브라우저에서 `http://localhost:8000/search.html`로 접속합니다.

## 한계와 후속 작업

- 색인은 현재 브라우저가 한 번에 내려받는 JSON 배열입니다. 자료가 커지면 색인 분할 또는 Pagefind 등 정적 검색 엔진으로 이전해야 합니다.
- 제목·요약 기반 규칙 분류이므로 오분류와 누락이 있을 수 있습니다. 검증 데이터셋으로 정확도를 측정해야 합니다.
- 문제 해결 경로는 기사 내용 자체를 검증하지 않습니다. 분류된 검색 결과를 단계별로 보여주는 탐색 보조 기능입니다.
- RSS 원문은 복제하지 않으며 수집한 메타데이터와 원문 링크를 제공합니다.
- 매일 배포는 GitHub Actions 예약 실행 성공을 전제로 합니다. 예약 실행은 지연되거나 건너뛸 수 있습니다.
- GitHub Actions 실행 및 실제 브라우저 동작 확인 후 Draft PR을 리뷰 가능한 상태로 변경합니다.

## 개발 순서 제안

1. PR CI 및 브라우저 테스트 확인
2. 검색 색인 크기 측정 및 분할 기준 수립
3. 정확한 기술 동의어와 문서 유형 사전 개선
4. 공식 문서 연결과 관계 추천
5. 검색 품질 평가 및 추천 순서 튜닝
