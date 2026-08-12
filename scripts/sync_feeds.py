"""
피드 목록 동기화.

두 개의 공개 저장소에서 기업·기관 기술블로그 목록을 받아 data/feeds.json 으로 만든다.
개인 블로그는 제외한다.

  국내: awesome-devblog/db_community.yml  (단체·기업 블로그 파일)
  해외: kilimchoi/engineering-blogs OPML  (기업 블로그 위주 큐레이션)

주 1회 정도만 돌리면 된다.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"

KR_URL = ("https://raw.githubusercontent.com/awesome-devblog/"
          "awesome-devblog/master/db_community.yml")
EN_URL = ("https://raw.githubusercontent.com/kilimchoi/"
          "engineering-blogs/master/engineering_blogs.opml")
# OPML 은 기업/개인이 섞인 평면 목록이다. 어느 항목이 기업인지는
# README 의 "Companies" 섹션에만 나와 있어서, 이름 기준으로 대조한다.
EN_README = ("https://raw.githubusercontent.com/kilimchoi/"
             "engineering-blogs/master/README.md")

# 원본 목록이 오래되어 주소가 바뀐 것들. 여기서 덮어쓴다.
OVERRIDE = {
    "우아한형제들": "https://techblog.woowahan.com/feed/",
    "쿠팡": "https://medium.com/feed/coupang-engineering",
    "Discord": "https://discord.com/blog/rss.xml",
    "GitHub": "https://github.blog/engineering/feed/",
}

# 두 목록 어디에도 없지만 품질이 좋은 곳들
EXTRA = [
    ("토스", "https://toss.tech/rss.xml", "KR"),
    ("Figma", "https://www.figma.com/blog/engineering/feed/atom.xml", "EN"),
    ("PlanetScale", "https://planetscale.com/blog/rss.xml", "EN"),
    ("Zerodha Tech", "https://zerodha.tech/rss.xml", "EN"),
]

ITEM_RE = re.compile(r"^\*\s+(.+?)\s+(https?://\S+)\s*$")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "devblog-collector/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_kr() -> list[dict]:
    rows = yaml.safe_load(fetch(KR_URL).decode("utf-8"))
    out = []
    for x in rows:
        rss = x.get("rss")
        if not rss:
            continue
        out.append({
            "name": x["name"].strip(),
            "feed_url": rss.strip(),
            "site_url": (x.get("blog") or x.get("home") or "").strip(),
            "region": "KR",
        })
    return out


def company_names() -> set[str]:
    """README 의 '### Companies' 섹션에 들어 있는 이름만 뽑는다.

    다음 '### ' 헤딩(Individuals) 을 만나면 멈춘다.
    """
    lines = fetch(EN_README).decode("utf-8").splitlines()
    names, inside = set(), False
    for line in lines:
        if line.startswith("### "):
            inside = line.strip() == "### Companies"
            continue
        if not inside:
            continue
        m = ITEM_RE.match(line)
        if m:
            names.add(m.group(1).strip().lower())
    return names


def load_en() -> list[dict]:
    companies = company_names()
    root = ET.fromstring(fetch(EN_URL))
    out, skipped = [], 0
    for o in root.iter("outline"):
        rss = o.get("xmlUrl")
        if not rss:
            continue
        name = (o.get("text") or o.get("title") or "").strip()
        if name.lower() not in companies:
            skipped += 1          # 개인 블로그이거나 README 와 이름이 어긋난 항목
            continue
        out.append({
            "name": name,
            "feed_url": rss.strip(),
            "site_url": (o.get("htmlUrl") or "").strip(),
            "region": "EN",
        })
    print(f"  해외: 기업 {len(out)}개 채택 / {skipped}개 제외(개인·불일치)")
    return out


def normalize_feed_url(url: str) -> tuple:
    """중복 판정용. www 와 끝 슬래시 차이는 같은 피드로 본다."""
    u = urlparse(url.lower())
    return u.netloc.replace("www.", ""), u.path.rstrip("/")


def main() -> int:
    feeds = load_kr() + load_en() + [
        {"name": n, "feed_url": u, "site_url": "", "region": r} for n, u, r in EXTRA
    ]

    for f in feeds:
        if f["name"] in OVERRIDE:
            f["feed_url"] = OVERRIDE[f["name"]]

    seen, merged = set(), []
    for f in feeds:
        key = normalize_feed_url(f["feed_url"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(f)

    merged.sort(key=lambda x: (x["region"], x["name"].lower()))

    DATA.mkdir(exist_ok=True)
    path = DATA / "feeds.json"
    path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    kr = sum(1 for f in merged if f["region"] == "KR")
    print(f"feeds.json 갱신: 총 {len(merged)}개 (국내 {kr} / 해외 {len(merged) - kr})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
