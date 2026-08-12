# 기업·기관의 문제해결을 보고 배우자

국내외 **기업·기관**의 새 글을 매일 모아 최신순으로 보여준다.
개인 블로그는 제외한다.

DB 서버가 없다. 상태는 전부 저장소 안의 파일에 있고, GitHub Actions 가 매일 돌려서 커밋한다.

# 만든 이유
국내외 기업·기관들의 프로그래밍 능력을 배우고자 새 글을 매일 모아 공부하기 위하여 만들었음.

## 빠른 시작

```bash
pip install -r requirements.txt

python scripts/sync_feeds.py   # 피드 목록 받아오기 (가끔)
python scripts/collect.py      # 새 글 수집 (매일)
python scripts/render.py       # HTML 만들기

open public/index.html
```

## 저장소에 올리고 자동화하기

1. GitHub 에 저장소를 만들고 push
2. Settings → Pages → Source 를 **GitHub Actions** 로
3. Actions 탭 → `collect` → **Run workflow** 로 한 번 수동 실행

이후 매일 KST 06:00 경에 자동으로 돈다.

## 구조

```
scripts/
  sync_feeds.py   피드 목록 동기화 (외부 저장소 두 곳 → data/feeds.json)
  collect.py      RSS 수집 → data/articles/YYYY-MM.jsonl
  render.py       → public/index.html
data/
  feeds.json        피드 목록 (390개)
  articles/*.jsonl  글 본체. 한 줄 = 글 하나
  seen.txt          수집한 글의 url_hash. 중복 방지용
  feed_state.json   피드별 ETag / 실패 횟수
```

### 피드 출처

| 지역 | 출처 | 비고 |
|---|---|---|
| 국내 191 | [awesome-devblog](https://github.com/awesome-devblog/awesome-devblog) `db_community.yml` | 단체·기업 파일. `db.yml`(개인 2,333개)은 안 씀 |
| 해외 199 | [kilimchoi/engineering-blogs](https://github.com/kilimchoi/engineering-blogs) | OPML 은 개인이 섞여 있어 README 의 `Companies` 섹션과 대조해 걸러냄 |

## 설계 메모

**왜 SQLite 를 안 쓰나.** 바이너리 파일은 git 이 델타 압축을 못 한다. 매일 커밋하면 한 줄 바뀌어도 파일 전체가 히스토리에 쌓인다. JSONL 은 텍스트라 추가된 줄만 저장된다.

**중복 판정.** RSS 의 `guid` 는 형식이 제각각이고 없는 피드도 있어서 안 쓴다. URL 을 정규화(`www.` 제거, 끝 슬래시 제거, 쿼리스트링 버림)한 뒤 SHA-256 앞 32자를 키로 쓴다.

**조건부 GET.** 응답의 `ETag` / `Last-Modified` 를 저장해 두었다가 다음 요청에 `If-None-Match` / `If-Modified-Since` 로 보낸다. 대부분 304 로 끝나서 파싱을 건너뛴다.

**실패 격리.** 예외는 피드 단위로 잡는다. 연속 3회 실패하면 그 피드는 다음부터 건너뛴다. 죽은 피드가 배치 시간을 잡아먹는 걸 막는다. 첫 실행 시 실패율 20~30% 는 정상이다 — 원본 목록에 옛 주소가 남아 있다.

**날짜.** `published` 가 없는 피드가 있고, 미래 날짜가 찍힌 피드도 있다. 미래 날짜는 수집일로 누르고, 없으면 수집일로 대체해 정렬한다. 블로그 이전 등으로 오래된 글이 한꺼번에 들어오면 목록에 `(N일 전 글)` 로 표시한다.

**필터링은 하지 않는다.** 키워드가 걸린 글에 표시(●)만 달고 전부 보여준다. 걸러버리면 뭘 놓쳤는지 알 방법이 없다.

## 알아둘 것

- 첫 실행 시 피드당 최근 10~20건씩 들어와 **수천 건**이 한꺼번에 쌓인다. 그 이후로는 하루 30~60건 수준
- RSS 는 최근 글만 준다. 과거 아카이브는 못 가져온다
- Actions 스케줄은 정시를 보장하지 않는다. 수십 분 밀리거나 가끔 건너뛴다
  ㄴ 그리하여 가져오는 일정을 8일로 잡음
- 저장소가 60일간 활동이 없으면 예약 워크플로가 자동 비활성화된다
- `data/feeds.json` 은 한 번 눈으로 훑고 필요 없는 곳을 지우는 게 좋다
  ㄴ 한번 실패된 사이트의 경우 삭제되도록 처리
