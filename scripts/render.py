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
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
       "Helvetica Neue", sans-serif; max-width: 860px; margin: 0 auto;
       padding: 24px 16px 80px; line-height: 1.5; }
h1 { font-size: 20px; margin: 0 0 4px; }
.meta { color: #888; font-size: 13px; margin-bottom: 20px; }
#q { width: 100%; padding: 10px 12px; font-size: 15px; border: 1px solid #ccc;
     border-radius: 8px; margin-bottom: 8px; }
.tabs { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.tab { padding: 5px 12px; font-size: 13px; border: 1px solid #ccc;
       border-radius: 999px; cursor: pointer; background: none; color: inherit; }
.tab.on { background: #333; color: #fff; border-color: #333; }
.day { font-size: 13px; font-weight: 600; color: #888; margin: 22px 0 8px;
       border-bottom: 1px solid #e5e5e5; padding-bottom: 4px; }
.item { padding: 7px 0; }
.item a { color: inherit; text-decoration: none; font-size: 15px; }
.item a:hover { text-decoration: underline; }
.src { font-size: 12px; color: #999; margin-left: 6px; white-space: nowrap; }
.hit { color: #b45309; font-weight: 600; }
.sum { font-size: 13px; color: #888; margin-top: 2px;
       overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.late { font-size: 11px; color: #aaa; }
.archive { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e5e5;
           font-size: 12px; color: #999; display: flex; flex-wrap: wrap;
           gap: 10px; align-items: center; }
.archive a { color: #999; }
@media (prefers-color-scheme: dark) {
  body { background: #16181c; color: #e8e8e8; }
  .day { border-color: #2c2f36; }
  #q, .tab { border-color: #3a3d44; background: #1d2026; color: #e8e8e8; }
  .tab.on { background: #e8e8e8; color: #16181c; }
}
"""

JS = """
const q = document.getElementById('q');
const items = [...document.querySelectorAll('.item')];
let region = 'ALL';

function apply() {
  const term = q.value.trim().toLowerCase();
  items.forEach(el => {
    const okR = region === 'ALL' || el.dataset.region === region;
    const okQ = !term || el.dataset.search.includes(term);
    el.style.display = (okR && okQ) ? '' : 'none';
  });
  document.querySelectorAll('.day').forEach(d => {
    let n = d.nextElementSibling, any = false;
    while (n && n.classList.contains('item')) {
      if (n.style.display !== 'none') any = true;
      n = n.nextElementSibling;
    }
    d.style.display = any ? '' : 'none';
  });
}
q.addEventListener('input', apply);
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  t.classList.add('on');
  region = t.dataset.region;
  apply();
}));
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
        "<title>기술블로그 모아보기</title>",
        f"<style>{CSS}</style></head><body>",
        "<h1>기술블로그 모아보기</h1>",
        f"<div class='meta'>최근 {DAYS}일 · {len(recent)}건 · "
        f"누적 {len(articles)}건 · 갱신 "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</div>",
        "<input id='q' placeholder='제목·회사·요약 검색'>",
        "<div class='tabs'>"
        "<button class='tab on' data-region='ALL'>전체</button>"
        "<button class='tab' data-region='KR'>국내</button>"
        "<button class='tab' data-region='EN'>해외</button></div>",
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

    parts.append(f"<script>{JS}</script></body></html>")

    dated, past_count = write_output("\n".join(parts))
    print(f"{dated.name} 생성: {len(recent)}건 표시")
    print(f"index.html 갱신" + (f" (지난 기록 {past_count}개 링크)" if past_count else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
