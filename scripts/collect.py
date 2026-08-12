"""
피드 수집.

data/feeds.json 의 모든 피드를 병렬로 받아, 새 글만 data/articles/YYYY-MM.jsonl 에 덧붙인다.

DB 를 쓰지 않으므로 상태는 전부 파일에 있다.
  data/seen.txt        이미 수집한 글의 url_hash 목록 (중복 방지)
  data/feed_state.json 피드별 ETag / Last-Modified / 연속 실패 횟수
"""
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARTICLES = DATA / "articles"

TIMEOUT = 15
WORKERS = 16
MAX_FAIL = 3          # 연속 실패가 이 횟수에 닿으면 피드를 쉬게 한다
MAX_AGE_DAYS = 30     # 이보다 오래된 글은 저장하지 않는다
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 브라우저는 이 헤더들을 항상 같이 보낸다. UA 만 바꾸면 조합이 어색해서
# Cloudflare 같은 봇 방어에 걸린다.
BASE_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ── URL 정규화 ────────────────────────────────────────────────
TRACKING = re.compile(r"^(utm_|ref$|source$|fbclid$|gclid$)")


def normalize(url: str) -> str:
    u = urlparse(url.strip())
    host = u.netloc.lower().replace("www.", "")
    path = u.path.rstrip("/")
    return f"{host}{path}"


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize(url).encode()).hexdigest()[:32]


# ── 날짜 ──────────────────────────────────────────────────────
def parse_date(entry) -> str | None:
    """RSS 의 날짜 표기는 제각각이라 방어적으로 읽는다."""
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc).date().isoformat()
        except (TypeError, ValueError):
            pass
        # feedparser 가 구조체로 파싱해 둔 경우
        st = entry.get(key + "_parsed")
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc).date().isoformat()
            except ValueError:
                pass
    return None


def clean_text(html: str, limit: int = 400) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&[a-z]+;|&#\d+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


# ── 피드 하나 처리 ────────────────────────────────────────────
def fetch_feed(feed: dict, state: dict) -> tuple[str, list[dict], dict]:
    """(결과종류, 글목록, 갱신된 상태) 를 돌려준다. 예외를 밖으로 던지지 않는다."""
    url = feed["feed_url"]
    st = dict(state.get(url, {}))
    headers = dict(BASE_HEADERS)
    if st.get("etag"):
        headers["If-None-Match"] = st["etag"]
    if st.get("last_modified"):
        headers["If-Modified-Since"] = st["last_modified"]

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        st["fail_count"] = st.get("fail_count", 0) + 1
        st["last_error"] = type(e).__name__
        return "error", [], st

    st["last_status"] = r.status_code
    st["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if r.status_code == 304:
        st["fail_count"] = 0
        return "not_modified", [], st

    if r.status_code != 200:
        st["fail_count"] = st.get("fail_count", 0) + 1
        return "error", [], st

    st["fail_count"] = 0
    st.pop("last_error", None)
    if r.headers.get("ETag"):
        st["etag"] = r.headers["ETag"]
    if r.headers.get("Last-Modified"):
        st["last_modified"] = r.headers["Last-Modified"]

    parsed = feedparser.parse(r.content)
    today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()
    cutoff = (today - timedelta(days=MAX_AGE_DAYS)).isoformat()

    items = []
    for e in parsed.entries:
        link = e.get("link")
        if not link:
            continue
        published = parse_date(e)
        # 발행일이 미래로 찍힌 피드가 실제로 있다. 수집일로 눌러 둔다.
        if published and published > today_str:
            published = today_str
        # 발행일이 없으면 버리지 않고 통과시킨다. 오늘 처음 본 글이기 때문.
        if published and published < cutoff:
            continue
        items.append({
            "hash": url_hash(link),
            "title": clean_text(e.get("title", ""), 300) or "(제목 없음)",
            "url": link.strip(),
            "summary": clean_text(e.get("summary", "")),
            "published": published,
            "collected": today_str,
            "feed": feed["name"],
            "region": feed["region"],
        })
    return "ok", items, st


# ── 저장 ──────────────────────────────────────────────────────
def append_articles(items: list[dict]) -> int:
    """월별 파일에 덧붙인다. 텍스트라서 git 이 추가된 줄만 저장한다."""
    ARTICLES.mkdir(parents=True, exist_ok=True)
    by_month = defaultdict(list)
    for it in items:
        month = (it["published"] or it["collected"])[:7]
        by_month[month].append(it)

    for month, rows in by_month.items():
        path = ARTICLES / f"{month}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(items)


def main() -> int:
    feeds = json.loads((DATA / "feeds.json").read_text(encoding="utf-8"))

    state_path = DATA / "feed_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    seen_path = DATA / "seen.txt"
    seen = set(seen_path.read_text(encoding="utf-8").split()) if seen_path.exists() else set()

    active = [f for f in feeds if state.get(f["feed_url"], {}).get("fail_count", 0) < MAX_FAIL]
    print(f"대상 피드 {len(active)}개 (전체 {len(feeds)}, 휴면 {len(feeds) - len(active)})")

    start = time.time()
    stats = defaultdict(int)
    new_items = []

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = pool.map(lambda f: (f, *fetch_feed(f, state)), active)

        for feed, kind, items, st in results:
            state[feed["feed_url"]] = st
            stats[kind] += 1
            if kind == "error":
                print(f"  실패({st.get('fail_count')}회) {feed['name']}: "
                      f"{st.get('last_error') or st.get('last_status')}")
            for it in items:
                if it["hash"] in seen:
                    continue
                seen.add(it["hash"])          # 같은 배치 안 중복도 여기서 걸린다
                new_items.append(it)

    added = append_articles(new_items)
    seen_path.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")

    print(f"\n갱신 {stats['ok']} / 변경없음 {stats['not_modified']} / 실패 {stats['error']}")
    print(f"새 글 {added}건, 누적 {len(seen)}건, {time.time() - start:.1f}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
