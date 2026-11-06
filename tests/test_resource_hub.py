"""Offline integration tests for the public resource hub builder."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_resource_hub import (
    EXPERIENCE_NAMES,
    build,
    load_designs,
    load_prompts,
    prompt_body,
)


class HubBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prompt_root = self.root / "prompt-library"
        self.prompt_dir = self.prompt_root / "prompts" / "learning"
        self.prompt_dir.mkdir(parents=True)
        self.prompt_file = self.prompt_dir / "study-plan.md"
        self.prompt_file.write_text(
            "# 학습 계획\n\n**사용 상황:** 시험 준비\n\n"
            "## 복사해서 사용하는 프롬프트\n\n"
            "나의 목표: [입력]\n\n## 사용 팁\n\n계획 조정\n",
            encoding="utf-8",
        )
        self.design_file = self.root / "designs.json"
        self.design_file.write_text(json.dumps([
            {"id": "001", "name": "테스트 시안", "layout": "cards",
             "layoutName": "카드", "description": "테스트 화면", "styleName": "잉크"}
        ], ensure_ascii=False), encoding="utf-8")
        self.output = self.root / "public" / "hub-data.json"

    def test_prompt_excerpt_excludes_usage_tips(self):
        text = self.prompt_file.read_text(encoding="utf-8")
        self.assertEqual(prompt_body(text), "나의 목표: [입력]")
        prompts = load_prompts(self.prompt_root)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["title"], "학습 계획")
        self.assertEqual(prompts[0]["category_label"], "학습")
        self.assertEqual(prompts[0]["description"], "시험 준비")
        self.assertIn("prompts/learning/study-plan.md", prompts[0]["url"])

    def test_headingless_copy_section_keeps_document(self):
        self.assertEqual(prompt_body("# 보안 점검\n\n입력: [저장소]"),
                         "# 보안 점검\n\n입력: [저장소]")

    def test_build_writes_stable_unicode_json(self):
        first = build(self.prompt_root, self.design_file, self.output)
        bytes_before = self.output.read_bytes()
        second = build(self.prompt_root, self.design_file, self.output)
        self.assertEqual(bytes_before, self.output.read_bytes())
        self.assertEqual(first, second)
        self.assertEqual(first["counts"]["prompts"], 1)
        self.assertEqual(first["counts"]["designs"], 1)
        self.assertEqual(first["counts"]["experiences"], 42)
        self.assertEqual(len(EXPERIENCE_NAMES), 42)
        self.assertIn("학습 계획", self.output.read_text(encoding="utf-8"))
        self.assertNotIn("dev-kit", self.output.read_text(encoding="utf-8"))
        self.assertEqual(first["items"][1]["url"],
                         "https://lealle.github.io/design-atlas/designs/001.html")

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

    def test_missing_inputs_do_not_overwrite_previous_index(self):
        build(self.prompt_root, self.design_file, self.output)
        previous = self.output.read_bytes()
        self.prompt_file.unlink()
        with self.assertRaises(ValueError):
            build(self.prompt_root, self.design_file, self.output)
        self.assertEqual(previous, self.output.read_bytes())


if __name__ == "__main__":
    unittest.main()
