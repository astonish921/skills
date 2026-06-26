from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import load_skill_module


class DummyBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        target = Path(kwargs["output_dir"]) / kwargs["filename"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"png")
        return str(target)


class CliSingleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = load_skill_module("detail_flow_use_image_api", "detail_flow_use_image_api.py")

    def test_single_mode_creates_project_manifest_by_default(self) -> None:
        backend = DummyBackend()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with mock.patch.dict("os.environ", {"IMAGE_BACKEND": "openai"}, clear=True):
                with mock.patch.object(self.cli, "_workspace_root", return_value=workspace):
                    with mock.patch.object(self.cli, "import_backend", return_value=backend):
                        result = self.cli.main(["A clean master prompt", "--topic-hint", "demo"])
                        self.assertEqual(result["mode"], "single")
                        self.assertEqual(result["backend"], "openai")
                        self.assertTrue(result["output_path"].endswith("image.png"))
                        self.assertTrue(Path(result["manifest_path"]).exists())

    def test_single_mode_respects_output_dir_filename_and_model(self) -> None:
        backend = DummyBackend()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "images"
            out_dir.mkdir()
            with mock.patch.dict("os.environ", {"IMAGE_BACKEND": "openai"}, clear=True):
                with mock.patch.object(self.cli, "import_backend", return_value=backend):
                    result = self.cli.main(
                        [
                            "A 1:3 continuity master",
                            "--output-dir",
                            str(out_dir),
                            "--filename",
                            "product_master_1x3.png",
                            "--aspect-ratio",
                            "1:3",
                            "--model",
                            "gpt-image-2",
                        ]
                    )

        self.assertEqual(Path(result["output_path"]).name, "product_master_1x3.png")
        self.assertEqual(backend.calls[0]["aspect_ratio"], "1:3")
        self.assertEqual(backend.calls[0]["model"], "gpt-image-2")

    def test_single_mode_passes_reference_image_for_gemini(self) -> None:
        backend = DummyBackend()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "images"
            out_dir.mkdir()
            reference_image = Path(tmp) / "product.png"
            reference_image.write_bytes(b"product-bytes")
            with mock.patch.dict("os.environ", {"IMAGE_BACKEND": "gemini"}, clear=True):
                with mock.patch.object(self.cli, "import_backend", return_value=backend):
                    self.cli.main(
                        [
                            "Keep the product structure consistent",
                            "--output-dir",
                            str(out_dir),
                            "--reference-image",
                            str(reference_image),
                        ]
                    )

        self.assertEqual(backend.calls[0]["reference_image"], str(reference_image))


if __name__ == "__main__":
    unittest.main()
