from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from helpers import load_skill_module


class ProjectPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project_paths = load_skill_module("project_paths")

    def test_slugify_topic_uses_detail_flow_fallback(self) -> None:
        self.assertEqual(self.project_paths.slugify_topic(""), "detail-flow-image")
        self.assertEqual(
            self.project_paths.slugify_topic("Detail Page Master Prompt"),
            "detail-page-master-prompt",
        )

    def test_create_project_paths_creates_numbered_project_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first = self.project_paths.create_project_paths(workspace, "Smart Fan")
            second = self.project_paths.create_project_paths(workspace, "Smart Fan")

        self.assertEqual(first.project_slug, "smart-fan")
        self.assertEqual(second.project_slug, "smart-fan-2")
        self.assertTrue(first.images_dir.name == "images")
        self.assertTrue(second.manifest_path.name == "image_prompts.json")

    def test_ensure_unique_file_appends_numeric_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "screen_01.png"
            base.write_bytes(b"first")
            unique = self.project_paths.ensure_unique_file(base)

        self.assertEqual(unique.name, "screen_01_2.png")


if __name__ == "__main__":
    unittest.main()
