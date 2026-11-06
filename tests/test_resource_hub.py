"""Offline tests for a public-only design index.

The private Prompt Library and DevKit must NEVER be indexed by this builder.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_resource_hub import EXPERIENCE_NAMES, build, load_designs


class HubBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.design_file = self.root / "designs.json"
        self.design_file.write_text(json.dumps([
            {"id": "001", "name": "테스트 시안", "layout": "cards",
             "layoutName": "카드", "description": "테스트 화면", "styleName": "잉크"}
        ], ensure_ascii=False), encoding="utf-8")
        self.output = self.root / "public" / "hub-data.json"

    def test_build_writes_stable_unicode_json(self):
        first = build(self.design_file, self.output)
        before = self.output.read_bytes()
        second = build(self.design_file, self.output)
        self.assertEqual(before, self.output.read_bytes())
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], 2)
        self.assertEqual(first["counts"]["designs"], 1)
        self.assertEqual(first["counts"]["experiences"], 42)
        self.assertEqual(len(EXPERIENCE_NAMES), 42)
        self.assertIn("테스트 시안", self.output.read_text(encoding="utf-8"))
        self.assertEqual(first["items"][0]["url"],
                         "https://lealle.github.io/design-atlas/designs/001.html")

    def test_private_content_is_not_indexed(self):
        fake = self.root / "_sources" / "prompt-library" / "prompts" / "secret"
        fake.mkdir(parents=True)
        (fake / "private.md").write_text("# PRIVATE SENTINEL", encoding="utf-8")
        data = build(self.design_file, self.output)
        published = self.output.read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE SENTINEL", published)
        self.assertNotIn("prompt-library", published)
        self.assertNotIn("dev-kit", published)
        self.assertEqual(set(data["source"]), {"designs"})
        self.assertTrue(all(item["kind"] in {"design", "experience"}
                            for item in data["items"]))

    def test_reject_duplicate_design_numbers(self):
        item = {"id": "001", "name": "동일"}
        self.design_file.write_text(json.dumps([item, item]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_designs(self.design_file)

    def test_reject_unsafe_design_id(self):
        self.design_file.write_text(
            json.dumps([{"id": "../bad"}]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid design id"):
            load_designs(self.design_file)

    def test_missing_input_does_not_overwrite_previous_index(self):
        build(self.design_file, self.output)
        previous = self.output.read_bytes()
        self.design_file.unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.design_file, self.output)
        self.assertEqual(previous, self.output.read_bytes())


if __name__ == "__main__":
    unittest.main()
