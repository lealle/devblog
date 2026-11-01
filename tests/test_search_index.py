"""Regression tests for the static full-archive search index."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_search_index import build_index

class SearchIndexTests(unittest.TestCase):
    def test_all_months_deduplicated_and_sorted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "2026-01.jsonl").write_text(
                json.dumps({"hash": "a", "url": "https://example.com/a", "title": "Old", "published": "2026-01-02"}) + "\n",
                encoding="utf-8",
            )
            (root / "2026-02.jsonl").write_text(
                "\n".join([
                    json.dumps({"hash": "b", "url": "https://example.com/b", "title": "New", "published": "2026-02-01"}),
                    json.dumps({"hash": "a", "url": "https://example.com/a", "title": "Updated", "published": "2026-01-02"})
                ]) + "\n",
                encoding="utf-8",
            )
            rows = build_index(root)
            self.assertEqual([r["hash"] for r in rows], ["b", "a"])
            self.assertEqual(rows[1]["title"], "Updated")

    def test_missing_url_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "2026-01.jsonl").write_text('{"hash":"a","title":"no url"}\n', encoding="utf-8")
            self.assertEqual(build_index(Path(temp)), [])

if __name__ == "__main__":
    unittest.main()
