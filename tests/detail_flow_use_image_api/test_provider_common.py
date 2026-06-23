from __future__ import annotations

import os
import unittest
from unittest import mock

from helpers import load_skill_module


class ProviderCommonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.common = load_skill_module("provider_common")

    def test_detect_image_extension_uses_content_type_and_bytes(self) -> None:
        png = b"\x89PNG\r\n\x1a\nrest"
        jpg = b"\xff\xd8\xffrest"
        self.assertEqual(self.common.detect_image_extension(png, "image/png"), ".png")
        self.assertEqual(self.common.detect_image_extension(jpg, None), ".jpg")

    def test_require_api_key_raises_with_supplied_message(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                self.common.require_api_key("OPENAI_API_KEY", message="missing key")

        self.assertEqual(str(ctx.exception), "missing key")

    def test_retry_delay_and_rate_limit_classification(self) -> None:
        self.assertTrue(self.common.is_rate_limit_error(RuntimeError("429 quota exceeded")))
        self.assertEqual(self.common.retry_delay(1, rate_limited=True), 20)
        self.assertEqual(self.common.retry_delay(0, rate_limited=False), 5)


if __name__ == "__main__":
    unittest.main()
