from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import load_skill_module


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_skill_module("config")

    def test_resolve_env_path_uses_skill_specific_home_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "cwd"
            skill_dir = root / "skill"
            workspace = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            skill_dir.mkdir()
            workspace.mkdir()
            home.mkdir()

            target = home / ".detail-flow-use-image-api" / ".env"
            target.parent.mkdir()
            target.write_text("IMAGE_BACKEND=openai\n", encoding="utf-8")

            with mock.patch.object(self.config.Path, "home", return_value=home):
                resolved = self.config.resolve_env_path(
                    cwd=cwd,
                    skill_dir=skill_dir,
                    workspace_root=workspace,
                )

            self.assertEqual(resolved, target)

    def test_load_prefixed_env_file_keeps_process_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "IMAGE_BACKEND=gemini\nOPENAI_API_KEY=file-key\nOPENAI_MODEL=gpt-image-2\n",
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "process-key"}, clear=True):
                loaded = self.config.load_prefixed_env_file(
                    prefixes=("IMAGE_", "OPENAI_"),
                    env_path=env_path,
                )

                self.assertEqual(os.environ["OPENAI_API_KEY"], "process-key")
                self.assertEqual(os.environ["IMAGE_BACKEND"], "gemini")
                self.assertEqual(loaded["OPENAI_MODEL"], "gpt-image-2")

    def test_validate_no_deprecated_image_keys_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.config.validate_no_deprecated_image_keys({"IMAGE_API_KEY": "old-key"})

        self.assertIn("IMAGE_API_KEY", str(ctx.exception))
        self.assertIn("provider-specific", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
