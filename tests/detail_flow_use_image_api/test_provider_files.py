from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "detail-flow-use-image-api"
PROVIDER_DIR = SKILL_DIR / "providers"

EXPECTED_PROVIDERS = [
    "openai",
    "gemini",
    "openrouter",
    "qwen",
    "zhipu",
    "volcengine",
    "minimax",
    "stability",
    "bfl",
    "ideogram",
    "siliconflow",
    "fal",
    "replicate",
    "modelscope",
]


class ProviderFileSmokeTests(unittest.TestCase):
    def test_all_expected_provider_files_exist(self) -> None:
        for name in EXPECTED_PROVIDERS:
            path = PROVIDER_DIR / f"{name}.py"
            self.assertTrue(path.exists(), path)

    def test_provider_sources_expose_generate_function(self) -> None:
        for name in EXPECTED_PROVIDERS:
            text = (PROVIDER_DIR / f"{name}.py").read_text(encoding="utf-8")
            self.assertIn("def generate(", text, name)

    def test_env_example_lists_image_backend(self) -> None:
        text = (SKILL_DIR / ".env.example").read_text(encoding="utf-8")
        self.assertIn("IMAGE_BACKEND", text)
        self.assertIn("OPENAI_API_KEY", text)
        self.assertIn("GEMINI_API_KEY", text)


if __name__ == "__main__":
    unittest.main()
