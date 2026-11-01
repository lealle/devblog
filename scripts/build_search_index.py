"""Build a compact, static, searchable catalogue from all collected articles."""
import json
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.classify_articles import classify
except ModuleNotFoundError:
    from classify_articles import classify

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "articles"
OUTPUT = ROOT / "public"
FIELDS = ("hash", "title", "url", "summary", "published", "collected", "feed", "region")

def build_index(source=SOURCE):
    by_id = {}
    for path in sorted(source.glob("????-??.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                article = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
            key = article.get("hash")
            if not key or not article.get("url") or urlsplit(article["url"]).scheme not in ("http", "https"):
                continue
            by_id[key] = {**{field: article.get(field, "") for field in FIELDS}, **classify(article)}
    return sorted(by_id.values(), key=lambda a: (a["published"] or a["collected"], a["hash"]), reverse=True)

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = build_index()
    (OUTPUT / "search-index.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"검색 색인 생성: {len(rows)}건")

if __name__ == "__main__":
    main()
