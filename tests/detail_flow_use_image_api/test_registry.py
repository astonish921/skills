from __future__ import annotations

import unittest

from helpers import load_skill_module


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_skill_module("registry")

    def test_registry_contains_expected_backends(self) -> None:
        expected = {
            "openai",
            "gemini",
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
            "openrouter",
            "modelscope",
        }
        self.assertEqual(set(self.registry.BACKEND_REGISTRY), expected)

    def test_aliases_resolve_to_canonical_names(self) -> None:
        self.assertEqual(self.registry.resolve_backend_name("dashscope"), "qwen")
        self.assertEqual(self.registry.resolve_backend_name("google"), "gemini")
        self.assertEqual(self.registry.resolve_backend_name("seedream"), "volcengine")

    def test_unsupported_backend_lists_supported_names(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.registry.resolve_backend_name("made-up-provider")

        self.assertIn("Unsupported IMAGE_BACKEND", str(ctx.exception))
        self.assertIn("openai", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
