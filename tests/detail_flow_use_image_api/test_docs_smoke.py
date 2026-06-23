from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "detail-flow-use-image-api"


class DocsSmokeTests(unittest.TestCase):
    def test_skill_markdown_mentions_explicit_api_execution(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: detail-flow-use-image-api", text)
        self.assertIn("detail_flow_use_image_api.py", text)
        self.assertIn("IMAGE_BACKEND", text)
        self.assertIn("project/<topic-slug>/images/", text)
        self.assertIn("two normal user approval gates", text)

    def test_readme_mentions_new_skill_name_and_entrypoint(self) -> None:
        text = (SKILL_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("detail-flow-use-image-api", text)
        self.assertIn("python skills/detail-flow-use-image-api/detail_flow_use_image_api.py", text)
        self.assertIn("IMAGE_BACKEND", text)

    def test_reference_doc_mentions_script_backed_generation(self) -> None:
        text = (SKILL_DIR / "references" / "detail-page-patterns.md").read_text(encoding="utf-8")
        self.assertIn("detail_flow_use_image_api.py", text)
        self.assertIn("1:3", text)
        self.assertIn("9:21", text)

    def test_agent_yaml_uses_new_display_name(self) -> None:
        text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "DetailFlow Use Image API"', text)
        self.assertIn("$detail-flow-use-image-api", text)


if __name__ == "__main__":
    unittest.main()
