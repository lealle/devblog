"""Regression checks for the reader UX and the public design-preview contract."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts import render


ROOT = Path(__file__).resolve().parent.parent


class ReadingUIGuardTests(unittest.TestCase):
    def test_render_preserves_articles_and_exposes_accessible_navigation(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td, "data")
            out = Path(td, "public")
            (data / "articles").mkdir(parents=True)
            row = {
                "title": "장애 대응 <테스트>", "url": "https://example.com/article",
                "feed": "테스트 회사", "summary": "빠른 원인 분석",
                "region": "KR", "published": date.today().isoformat(),
                "collected": date.today().isoformat()
            }
            (data / "articles" / (date.today().strftime("%Y-%m") + ".jsonl")).write_text(
                json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            with patch.object(render, "DATA", data), patch.object(render, "OUT", out):
                self.assertEqual(render.main(), 0)
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("class='reading-view'", html)
            self.assertIn("href='blog-ui.css'", html)
            self.assertIn("id='feed'", html)
            self.assertIn("id='status'", html)
            self.assertIn("id='empty'", html)
            self.assertIn("aria-pressed='true'", html)
            self.assertIn("https://example.com/article", html)
            self.assertIn("장애 대응 &lt;테스트&gt;", html)
            self.assertNotIn("장애 대응 <테스트>", html)

    def test_search_page_keeps_core_filter_contract(self):
        html = (ROOT / "public/search.html").read_text(encoding="utf-8")
        for tag in ['id="q"', 'id="region"', 'id="topic"', 'id="sort"',
                    'id="mode-general"', 'id="mode-solve"', 'id="results"',
                    'id="status"', 'id="more"', 'href="blog-ui.css"']:
            self.assertIn(tag, html)
        self.assertIn('class="suggestions"', html)
        self.assertIn('class="search-view"', html)
        self.assertIn("search-index.json", html)

    def test_preview_markup_and_private_data_exclusion(self):
        html = (ROOT / "public/hub.html").read_text(encoding="utf-8")
        script = (ROOT / "public/hub.js").read_text(encoding="utf-8")
        css = (ROOT / "public/hub-refresh.css").read_text(encoding="utf-8")
        data = json.loads((ROOT / "public/hub-data.json").read_text(encoding="utf-8"))
        for marker in ('id="preview-dialog"', 'id="preview-title"',
                       'id="preview-viewport"', 'id="preview-close"',
                       'id="preview-modes"', 'id="preview-original"'):
            self.assertIn(marker, html)
        self.assertIn("frame-src 'self'", html)
        self.assertIn('href="./hub-refresh.css?v=20261106b"', html)
        self.assertIn("IntersectionObserver", script)
        self.assertIn('frame.loading = thumbnail ? "lazy"', script)
        self.assertIn('frame.src = previewUrl(item, state.mode)', script)
        self.assertIn("showModal()", script)
        self.assertIn(".preview-thumbnail", css)
        self.assertIn("allow-scripts allow-same-origin", script)
        self.assertTrue(all(item["kind"] in {"design", "experience"} for item in data["items"]))
        self.assertEqual(len(data["items"]), 142)
        self.assertEqual(set(data["source"]), {"designs"})


if __name__ == "__main__":
    unittest.main()
