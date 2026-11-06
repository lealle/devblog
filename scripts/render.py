"""
수집한 글을 최신순 정적 HTML 한 장으로 만든다.

GitHub Pages 로 뿌리면 어디서든 볼 수 있다. 필터링은 하지 않고 전부 보여준다.
관심 키워드가 걸린 글에만 표시를 달아 눈이 먼저 가게 한다.
"""
import html
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "public"

DAYS = 8         # 최근 며칠치를 보여줄지
PURGE_AFTER_DAYS = 90   # 이보다 오래된 날짜 파일은 지운다

# 걸러내는 용도가 아니라 표시하는 용도
KEYWORDS = [
    "성능", "장애", "회고", "개선", "마이그레이션", "동시성", "대용량", "트래픽",
    "최적화", "병목", "튜닝", "리팩터링", "부하",
    "scaling", "scale", "migrating", "migration", "latency", "throughput",
    "postmortem", "incident", "outage", "bottleneck", "optimization",
    "deadlock", "sharding", "concurrency", "performance",
]


def load_articles() -> list[dict]:
    rows = []
    for path in sorted((DATA / "articles").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sort_key(a: dict) -> str:
    """발행일이 없으면 수집일로 대체. 미래 날짜는 수집 단계에서 이미 눌렀다."""
    return a.get("published") or a.get("collected") or "0000-00-00"


def matched(a: dict) -> list[str]:
    text = (a["title"] + " " + a.get("summary", "")).lower()
    return [k for k in KEYWORDS if k.lower() in text]


CSS = """
:root {
  color-scheme: light dark;
  --paper: #f7f8f4;
  --surface: #ffffff;
  --ink: #18332f;
  --muted: #52645e;
  --line: #d3ddd5;
  --brand: #176451;
  --soft: #e7efe8;
  --accent: #8b4d16;
}
* { box-sizing: border-box; }
html { background: var(--paper); }
body {
  max-width: 960px; margin: 0 auto; padding: 48px 28px 80px;
  background: var(--paper); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", "Malgun Gothic", sans-serif;
  font-size: 16px; line-height: 1.7; word-break: keep-all;
  overflow-wrap: anywhere;
}
a { color: var(--brand); text-underline-offset: 4px; }
a:hover { text-decoration: underline; }
header { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
h1 { font-size: clamp(28px, 4vw, 40px); line-height: 1.3; letter-spacing: -.045em; margin: 0 0 14px; font-weight: 750; }
header a, body > p > a { font-size: 14px; font-weight: 650; }
.eyebrow { color: var(--brand); font-size: 12px; font-weight: 750; letter-spacing: .16em; margin: 0 0 16px; }
.intro { max-width: 620px; color: var(--muted); margin: 0 0 24px; }
.meta, .src, .sum, .summary, .late, #status { color: var(--muted); }
.meta, #status { font-size: 13px; margin: 12px 0 24px; }
input, select, button { font: inherit; color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 6px; min-height: 44px; padding: 10px 14px; }
input { min-width: 0; }
#q { width: 100%; font-size: 16px; }
input::placeholder { color: var(--muted); opacity: 1; }
button { cursor: pointer; }
button:hover { border-color: var(--brand); }
:where(a, input, select, button):focus-visible { outline: 3px solid var(--brand); outline-offset: 4px; }
.tabs, .mode { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 30px; }
.tab { font-size: 14px; padding: 7px 18px; border-radius: 999px; }
.tab.on, .mode button[aria-pressed="true"] { background: var(--brand); border-color: var(--brand); color: var(--surface); }
.controls { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 10px; margin: 28px 0 12px; }
.controls input { grid-column: 1 / -1; }
.controls select { min-width: 0; }
.day { color: var(--brand); font-size: 13px; font-weight: 750; letter-spacing: .04em; margin: 36px 0 0; border-bottom: 2px solid var(--line); padding-bottom: 12px; }
.item { padding: 20px 0; border-bottom: 1px solid var(--line); }
.item a { color: var(--ink); font-size: 17px; font-weight: 650; line-height: 1.55; text-decoration: none; }
.item a:hover { color: var(--brand); text-decoration: underline; }
.src { display: block; font-size: 12px; margin: 7px 0 0; }
.sum { font-size: 14px; margin-top: 6px; line-height: 1.7; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; white-space: normal; }
.summary { font-size: 14px; line-height: 1.7; margin: 8px 0 0; }
.item .meta { font-size: 12px; margin: 7px 0 0; }
.late { font-size: 12px; }
.hit { color: var(--accent); }
.archive { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
.path { background: var(--soft); border: 1px solid var(--line); border-radius: 8px; padding: 22px; margin: 24px 0; }
.path h2 { font-size: 18px; margin: 0 0 10px; }
.path ol { margin: 0; padding-left: 22px; }
.path li { margin: 12px 0; }
.path small { display: block; color: var(--muted); }
#more { display: block; margin: 32px auto; padding-inline: 28px; }
[hidden] { display: none !important; }
@media (max-width: 640px) {
  body { padding: 30px 20px 60px; }
  header { align-items: flex-start; flex-direction: column; gap: 0; }
  header a { margin-bottom: 16px; }
  .controls { grid-template-columns: 1fr 1fr; }
  .controls #sort { grid-column: 1 / -1; }
  .item { padding: 18px 0; }
  .path { padding: 18px; }
}
@media (prefers-color-scheme: dark) {
  :root { --paper: #13221f; --surface: #1b2e29; --ink: #e4eee8; --muted: #aec1b6; --line: #40584e; --brand: #8bd5ba; --soft: #203b31; --accent: #e9b37e; }
  .tab.on, .mode button[aria-pressed="true"] { color: var(--paper); }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
"""

JS = """
const q = document.getElementById('q');
const items = [...document.querySelectorAll('.item')];
let region = 'ALL';

function apply() {
  const term = q.value.trim().toLowerCase();
  let visible = 0;
  items.forEach(el => {
    const okR = region === 'ALL' || el.dataset.region === region;
    const okQ = !term || el.dataset.search.includes(term);
    el.hidden = !(okR && okQ);
    if (!el.hidden) visible++;
  });
  document.querySelectorAll('.day').forEach(d => {
    let n = d.nextElementSibling, any = false;
    while (n && n.classList.contains('item')) {
      if (!n.hidden) any = true;
      n = n.nextElementSibling;
    }
    d.hidden = !any;
  });
  document.getElementById('status').textContent = visible + '건 표시 / 최근 전체 ' + items.length + '건';
  document.getElementById('empty').hidden = visible !== 0;
}
q.addEventListener('input', apply);
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  t.classList.add('on');
  document.querySelectorAll('.tab').forEach(x => x.setAttribute('aria-pressed', String(x === t)));
  region = t.dataset.region;
  apply();
}));
apply();
"""


def purge_old() -> list[str]:
    """PURGE_AFTER_DAYS 가 지난 날짜 파일을 지운다.

    원본은 data/articles/*.jsonl 에 그대로 있으므로 HTML 은 언제든 다시 만들 수 있다.
    """
    limit = (date.today() - timedelta(days=PURGE_AFTER_DAYS)).isoformat()
    removed = []
    for p in OUT.glob("????-??-??.html"):
        if p.stem < limit:
            p.unlink()
            removed.append(p.stem)
    return sorted(removed)


def write_output(body: str) -> tuple[Path, int]:
    """오늘 날짜 파일로 저장하고, index.html 은 그 사본으로 둔다.

    GitHub Pages 는 index.html 을 첫 화면으로 쓰기 때문에 둘 다 필요하다.
    """
    OUT.mkdir(exist_ok=True)
    today = date.today().isoformat()

    dated = OUT / f"{today}.html"
    dated.write_text(body, encoding="utf-8")

    purged = purge_old()
    if purged:
        print(f"오래된 파일 {len(purged)}개 삭제: {purged[0]} ~ {purged[-1]}")

    # 지난 날짜 파일이 있으면 index 하단에 링크를 붙인다
    past = sorted(
        (p for p in OUT.glob("????-??-??.html") if p.name != dated.name),
        reverse=True,
    )
    links = "".join(
        f"<a href='{p.name}'>{p.stem}</a>" for p in past
    )
    archive = (f"<div class='archive'><span>지난 기록</span>{links}</div>"
               if past else "")

    (OUT / "index.html").write_text(
        body.replace("</body>", f"{archive}</body>"), encoding="utf-8"
    )
    return dated, len(past)


def main() -> int:
    articles = load_articles()
    cutoff = (date.today() - timedelta(days=DAYS)).isoformat()
    recent = [a for a in articles if sort_key(a) >= cutoff]
    recent.sort(key=sort_key, reverse=True)

    parts = [
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta name='description' content='기업과 기관의 기술 블로그 글을 살펴보고 문제 해결 사례를 탐색합니다'>",
        "<title>DevBlog · 기술을 읽는 공간</title>",
        f"<style>{CSS}</style><link rel='stylesheet' href='blog-ui.css'></head><body class='reading-view'>",
        "<a class='skip-link' href='#feed'>기사 목록으로 건너뛰기</a>",
        "<header class='site-top'><a class='site-brand' href='index.html'>LEALLE <em>· DEV BLOG</em></a>",
        "<nav aria-label='주요 탐색'><a href='index.html' aria-current='page'>최신 글</a>",
        "<a href='search.html'>전체 검색</a><a href='hub.html'>통합 자료 허브</a></nav></header>",
        "<section class='editorial-hero' aria-labelledby='page-title'><div class='hero-copy'>",
        "<p class='eyebrow'>ENGINEERING / READING ROOM</p>",
        "<h1 id='page-title'>기술을 읽고,<br>해결의 실마리를 찾다.</h1>",
        "<p class='intro'>기업·기관의 실제 엔지니어링 경험을 날짜순으로 모았습니다. 관심 기술과 문제를 찾아 읽고, 실무에 적용할 근거를 확인하세요.</p>",
        "</div><div class='hero-stats' aria-label='수집 현황'>",
        f"<div class='stat'><strong>{len(recent):,}</strong><span>최근 {DAYS}일 기사</span></div>",
        f"<div class='stat'><strong>{len(articles):,}</strong><span>누적 수집</span></div>",
        "</div></section>",
        "<p class='updated-at'>최근 생성: " + datetime.now().strftime("%Y-%m-%d %H:%M") + " UTC · 원문은 각 출처에서 확인할 수 있습니다.</p>",
        "<div class='quick-nav'><a href='search.html'>전체 기술 문서 검색 ↗</a><a href='hub.html'>디자인·자료 허브 ↗</a></div>",
        "<section class='finder' aria-label='최신 기사 필터'>",
        "<label for='q'>제목·기업·요약에서 찾기</label>",
        "<input id='q' type='search' aria-label='최근 기사 검색' placeholder='예: 성능 최적화, 장애, 동시성'>",
        "<div class='tabs' role='group' aria-label='기사 지역'>",
        "<button type='button' class='tab on' data-region='ALL' aria-pressed='true'>전체 지역</button>",
        "<button type='button' class='tab' data-region='KR' aria-pressed='false'>국내</button>",
        "<button type='button' class='tab' data-region='EN' aria-pressed='false'>해외</button></div>",
        "<p class='search-hint'>최근 수집한 글만 검색합니다. 과거 기록까지 찾으려면 ‘전체 기술 문서 검색’을 선택하세요.</p></section>",
        "<div class='results-head'><h2>최근 수집한 글</h2><p id='status' role='status' aria-live='polite'></p></div>",
        "<main id='feed' class='feed-list' aria-label='최근 기술 블로그 글'>",
    ]

    current_day = None
    for a in recent:
        day = sort_key(a)
        if day != current_day:
            current_day = day
            parts.append(f"<div class='day'>{day}</div>")

        hits = matched(a)
        title = html.escape(a["title"])
        if hits:
            title = f"<span class='hit'>●</span> {title}"

        # 발행일보다 한참 뒤에 수집된 글은 표시해 둔다 (블로그 이전 등)
        late = ""
        if a.get("published") and a.get("collected") and a["collected"] > a["published"]:
            gap = (date.fromisoformat(a["collected"]) - date.fromisoformat(a["published"])).days
            if gap > 30:
                late = f" <span class='late'>({gap}일 전 글)</span>"

        search = html.escape(
            (a["title"] + " " + a["feed"] + " " + a.get("summary", "")).lower(), quote=True
        )
        parts.append(
            f"<div class='item' data-region='{a['region']}' data-search=\"{search}\">"
            f"<a href='{html.escape(a['url'])}' target='_blank' rel='noopener'>{title}</a>"
            f"<span class='src'>{html.escape(a['feed'])}</span>{late}"
            + (f"<div class='sum'>{html.escape(a.get('summary', '')[:160])}</div>"
               if a.get("summary") else "")
            + "</div>"
        )

    parts.append("</main><p class='empty-results' id='empty' hidden>조건에 맞는 글이 없습니다. 검색어 또는 지역을 바꿔 보세요.</p>")
    parts.append(f"<script>{JS}</script></body></html>")

    dated, past_count = write_output("\n".join(parts))
    print(f"{dated.name} 생성: {len(recent)}건 표시")
    print(f"index.html 갱신" + (f" (지난 기록 {past_count}개 링크)" if past_count else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
