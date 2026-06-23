from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import load_skill_module


class DummyBatchBackend:
    def generate(self, **kwargs):
        if kwargs["filename"] == "screen_02.png":
            raise RuntimeError("backend failed")
        target = Path(kwargs["output_dir"]) / kwargs["filename"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"png")
        return str(target)


class CliBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = load_skill_module("detail_flow_use_image_api", "detail_flow_use_image_api.py")

    def test_batch_mode_updates_statuses_in_manifest(self) -> None:
        payload = {
            "project": "demo",
            "items": [
                {
                    "filename": "screen_01.png",
                    "prompt": "slice one",
                    "aspect_ratio": "9:21",
                    "status": "Pending",
                },
                {
                    "filename": "screen_02.png",
                    "prompt": "slice two",
                    "aspect_ratio": "9:21",
                    "status": "Pending",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "image_prompts.json"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.dict("os.environ", {"IMAGE_BACKEND": "openai", "IMAGE_CONCURRENCY": "1"}, clear=True):
                with mock.patch.object(self.cli, "import_backend", return_value=DummyBatchBackend()):
                    result = self.cli.main(["--manifest", str(manifest_path)])

            saved = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(result["mode"], "batch")
        self.assertEqual(result["ok"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(saved["items"][0]["status"], "Generated")
        self.assertEqual(saved["items"][1]["status"], "Failed")
        self.assertIn("last_error", saved["items"][1])


if __name__ == "__main__":
    unittest.main()
