from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from helpers import load_skill_module


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_skill_module("manifest")

    def test_build_single_item_manifest_uses_supplied_filename(self) -> None:
        payload = self.manifest.build_single_item_manifest(
            "demo-skill",
            "A polished 1:3 master prompt",
            aspect_ratio="1:3",
            image_size="1K",
            filename="product_master_1x3.png",
        )

        item = payload["items"][0]
        self.assertEqual(payload["project"], "demo-skill")
        self.assertEqual(item["filename"], "product_master_1x3.png")
        self.assertEqual(item["aspect_ratio"], "1:3")
        self.assertEqual(item["status"], "Pending")

    def test_validate_manifest_rejects_duplicate_filenames(self) -> None:
        payload = {
            "items": [
                {
                    "filename": "screen_01.png",
                    "prompt": "first",
                    "aspect_ratio": "9:21",
                    "status": "Pending",
                },
                {
                    "filename": "screen_01.png",
                    "prompt": "second",
                    "aspect_ratio": "9:21",
                    "status": "Pending",
                },
            ]
        }

        with self.assertRaises(ValueError) as ctx:
            self.manifest.validate_manifest(payload, "inline")

        self.assertIn("duplicate filename", str(ctx.exception))

    def test_save_and_load_manifest_round_trip(self) -> None:
        payload = self.manifest.build_single_item_manifest("demo-skill", "Prompt text")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image_prompts.json"
            self.manifest.save_manifest(path, payload)
            loaded = self.manifest.load_manifest(path)

        self.assertEqual(loaded["items"][0]["prompt"], "Prompt text")


if __name__ == "__main__":
    unittest.main()
