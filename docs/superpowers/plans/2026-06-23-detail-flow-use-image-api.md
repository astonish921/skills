# detail-flow-use-image-api Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `detail-flow-use-image-api` skill that preserves the existing `detail-flow` blueprint and audit workflow while replacing every image-generation step with explicit `IMAGE_BACKEND`-driven API execution.

**Architecture:** Keep the new skill self-contained under `skills/detail-flow-use-image-api/`. Fork the workflow-facing documents from `detail-flow`, copy the backend and manifest runtime pieces from `image-gen-use-api`, then add a dedicated entrypoint that supports both one-off master generation and manifest-driven slice batches without importing the old skill at runtime.

**Tech Stack:** Markdown, YAML, Python 3, `argparse`, `pathlib`, `json`, `concurrent.futures`, `threading`, `unittest`, `unittest.mock`, `requests`, `Pillow`, optional `google-genai`

---

## File Structure

- `skills/detail-flow-use-image-api/SKILL.md`
  Main workflow document. This is the `detail-flow` fork that keeps the two approval gates and audit rules, but swaps generic image-generation language for explicit local API calls.

- `skills/detail-flow-use-image-api/README.md`
  Human-readable overview, installation, configuration, and examples for the new skill.

- `skills/detail-flow-use-image-api/.env.example`
  Provider configuration matrix for `IMAGE_BACKEND` and provider-specific keys.

- `skills/detail-flow-use-image-api/detail_flow_use_image_api.py`
  Dedicated CLI entrypoint for this skill. Supports single-image mode for masters and targeted reruns, plus manifest batch mode for slice sets.

- `skills/detail-flow-use-image-api/config.py`
  `.env` resolution and deprecated-image-key validation for the new skill.

- `skills/detail-flow-use-image-api/manifest.py`
  Manifest creation, validation, load, and save helpers.

- `skills/detail-flow-use-image-api/project_paths.py`
  Topic slug generation, project directory creation, and unique-filename helpers.

- `skills/detail-flow-use-image-api/registry.py`
  Backend registry, alias resolution, and provider lookup.

- `skills/detail-flow-use-image-api/provider_common.py`
  Shared HTTP and image-saving helpers used by the backend adapters.

- `skills/detail-flow-use-image-api/providers/__init__.py`
  Provider package marker.

- `skills/detail-flow-use-image-api/providers/*.py`
  Provider adapters copied from `image-gen-use-api`, kept local so this skill has no runtime dependency on the old one.

- `skills/detail-flow-use-image-api/references/detail-page-patterns.md`
  Reference guide copied from `detail-flow`, then adjusted so image-generation guidance points to explicit script-backed execution.

- `skills/detail-flow-use-image-api/agents/openai.yaml`
  Agent metadata for the new skill name and default prompt.

- `tests/detail_flow_use_image_api/helpers.py`
  Test loader for modules inside the hyphenated skill directory.

- `tests/detail_flow_use_image_api/test_config.py`
  Tests for `.env` resolution and deprecated-key handling.

- `tests/detail_flow_use_image_api/test_manifest.py`
  Tests for manifest creation and validation.

- `tests/detail_flow_use_image_api/test_project_paths.py`
  Tests for topic slug generation, project folder creation, and unique filenames.

- `tests/detail_flow_use_image_api/test_registry.py`
  Tests for backend registry coverage and alias resolution.

- `tests/detail_flow_use_image_api/test_provider_common.py`
  Tests for image-format detection, API-key lookup, retry delays, and rate-limit classification.

- `tests/detail_flow_use_image_api/test_provider_files.py`
  Smoke test that all expected local provider files exist and expose a `generate` function in source.

- `tests/detail_flow_use_image_api/test_cli_single.py`
  Tests for single-image orchestration, including `--output-dir` and `--filename` support.

- `tests/detail_flow_use_image_api/test_cli_batch.py`
  Tests for manifest batch execution and status write-back.

- `tests/detail_flow_use_image_api/test_docs_smoke.py`
  Smoke test for `SKILL.md`, `README.md`, `references/detail-page-patterns.md`, `.env.example`, and `agents/openai.yaml` content.

### Task 1: Create the new test harness and foundation modules

**Files:**
- Create: `tests/detail_flow_use_image_api/helpers.py`
- Create: `tests/detail_flow_use_image_api/test_config.py`
- Create: `tests/detail_flow_use_image_api/test_manifest.py`
- Create: `tests/detail_flow_use_image_api/test_project_paths.py`
- Create: `skills/detail-flow-use-image-api/config.py`
- Create: `skills/detail-flow-use-image-api/manifest.py`
- Create: `skills/detail-flow-use-image-api/project_paths.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/detail_flow_use_image_api/helpers.py`:

```python
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "detail-flow-use-image-api"


def load_skill_module(module_name: str, filename: str | None = None):
    module_path = SKILL_DIR / (filename or f"{module_name}.py")
    if str(SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(SKILL_DIR))
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
```

Create `tests/detail_flow_use_image_api/test_config.py`:

```python
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
```

Create `tests/detail_flow_use_image_api/test_manifest.py`:

```python
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
```

Create `tests/detail_flow_use_image_api/test_project_paths.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_config.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_manifest.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_project_paths.py" -v
```

Expected: FAIL with `FileNotFoundError` or import errors because the new skill directory and modules do not exist yet.

- [ ] **Step 3: Write the minimal implementation by copying the base modules and making the skill-local edits**

Create the directory and copy the baseline files:

```powershell
New-Item -ItemType Directory -Force "skills/detail-flow-use-image-api" | Out-Null
Copy-Item "skills/image-gen-use-api/config.py" "skills/detail-flow-use-image-api/config.py"
Copy-Item "skills/image-gen-use-api/manifest.py" "skills/detail-flow-use-image-api/manifest.py"
Copy-Item "skills/image-gen-use-api/project_paths.py" "skills/detail-flow-use-image-api/project_paths.py"
```

Replace `skills/detail-flow-use-image-api/config.py` with:

```python
from __future__ import annotations

import os
from pathlib import Path


DEPRECATED_IMAGE_KEYS = {
    "IMAGE_API_KEY": "Use IMAGE_BACKEND plus provider-specific keys such as OPENAI_API_KEY or GEMINI_API_KEY.",
    "IMAGE_MODEL": "Use provider-specific model keys such as OPENAI_MODEL or GEMINI_MODEL.",
    "IMAGE_BASE_URL": "Use provider-specific base URL keys such as OPENAI_BASE_URL or GEMINI_BASE_URL.",
}


def resolve_env_path(
    cwd: Path | None = None,
    skill_dir: Path | None = None,
    workspace_root: Path | None = None,
) -> Path | None:
    cwd = (cwd or Path.cwd()).resolve()
    skill_dir = (skill_dir or Path(__file__).resolve().parent).resolve()
    workspace_root = (workspace_root or cwd).resolve()

    candidates = [
        cwd / ".env",
        skill_dir / ".env",
        workspace_root / ".env",
        Path.home() / ".detail-flow-use-image-api" / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate_no_deprecated_image_keys(values: dict[str, str] | None = None) -> None:
    values = values or dict(os.environ)
    for key, replacement in DEPRECATED_IMAGE_KEYS.items():
        if values.get(key):
            raise ValueError(f"Unsupported image config key: {key}. {replacement}")


def load_prefixed_env_file(
    prefixes: tuple[str, ...],
    env_path: Path | None = None,
) -> dict[str, str]:
    env_path = env_path or resolve_env_path()
    if env_path is None or not env_path.exists():
        return {}

    file_values = parse_env_file(env_path)
    validate_no_deprecated_image_keys(file_values)

    loaded: dict[str, str] = {}
    for key, value in file_values.items():
        if not any(key.startswith(prefix) for prefix in prefixes):
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded
```

Replace `skills/detail-flow-use-image-api/project_paths.py` with:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path
    images_dir: Path
    manifest_path: Path
    project_slug: str


def slugify_topic(topic: str) -> str:
    raw = (topic or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return normalized or "detail-flow-image"


def create_project_paths(workspace_root: Path, topic: str) -> ProjectPaths:
    base_slug = slugify_topic(topic)
    project_base = workspace_root / "project"
    project_base.mkdir(parents=True, exist_ok=True)

    candidate = project_base / base_slug
    counter = 2
    while candidate.exists():
        candidate = project_base / f"{base_slug}-{counter}"
        counter += 1

    images_dir = candidate / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return ProjectPaths(
        project_root=candidate,
        images_dir=images_dir,
        manifest_path=images_dir / "image_prompts.json",
        project_slug=candidate.name,
    )


def ensure_unique_file(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
```

Keep `skills/detail-flow-use-image-api/manifest.py` identical to the existing `image-gen-use-api` version for now.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_config.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_manifest.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_project_paths.py" -v
```

Expected: PASS for all config, manifest, and project-path tests.

- [ ] **Step 5: Commit**

```bash
git add tests/detail_flow_use_image_api/helpers.py tests/detail_flow_use_image_api/test_config.py tests/detail_flow_use_image_api/test_manifest.py tests/detail_flow_use_image_api/test_project_paths.py skills/detail-flow-use-image-api/config.py skills/detail-flow-use-image-api/manifest.py skills/detail-flow-use-image-api/project_paths.py
git commit -m "feat: add detail-flow image api foundation"
```

### Task 2: Add registry and provider-common helpers

**Files:**
- Create: `tests/detail_flow_use_image_api/test_registry.py`
- Create: `tests/detail_flow_use_image_api/test_provider_common.py`
- Create: `skills/detail-flow-use-image-api/registry.py`
- Create: `skills/detail-flow-use-image-api/provider_common.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/detail_flow_use_image_api/test_registry.py`:

```python
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
```

Create `tests/detail_flow_use_image_api/test_provider_common.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_registry.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_provider_common.py" -v
```

Expected: FAIL because `registry.py` and `provider_common.py` do not exist yet.

- [ ] **Step 3: Implement the registry and shared provider helpers**

Copy the base files:

```powershell
Copy-Item "skills/image-gen-use-api/registry.py" "skills/detail-flow-use-image-api/registry.py"
Copy-Item "skills/image-gen-use-api/provider_common.py" "skills/detail-flow-use-image-api/provider_common.py"
```

Keep `skills/detail-flow-use-image-api/registry.py` as:

```python
from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSpec:
    module_name: str
    default_model: str
    aliases: tuple[str, ...] = ()


BACKEND_REGISTRY: dict[str, BackendSpec] = {
    "openai": BackendSpec("openai", "gpt-image-2", ("openai-compatible", "openai_compatible")),
    "gemini": BackendSpec("gemini", "gemini-3.1-flash-image-preview", ("google",)),
    "qwen": BackendSpec("qwen", "qwen-image-2.0-pro", ("dashscope",)),
    "zhipu": BackendSpec("zhipu", "glm-image", ("bigmodel", "glm")),
    "volcengine": BackendSpec("volcengine", "doubao-seedream-4-5-251128", ("ark", "doubao", "seedream")),
    "minimax": BackendSpec("minimax", "image-01", ("minimaxi",)),
    "stability": BackendSpec("stability", "stable-image-core", ("stabilityai",)),
    "bfl": BackendSpec("bfl", "flux-pro-1.1-ultra", ("flux", "black-forest-labs")),
    "ideogram": BackendSpec("ideogram", "ideogram-v3"),
    "siliconflow": BackendSpec("siliconflow", "Qwen/Qwen-Image", ("silicon",)),
    "fal": BackendSpec("fal", "fal-ai/imagen3/fast", ("fal-ai",)),
    "replicate": BackendSpec("replicate", "black-forest-labs/flux-1.1-pro"),
    "openrouter": BackendSpec("openrouter", "google/gemini-3.1-flash-image-preview"),
    "modelscope": BackendSpec("modelscope", "Tongyi-MAI/Z-Image-Turbo"),
}


def _build_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, spec in BACKEND_REGISTRY.items():
        aliases[canonical] = canonical
        for alias in spec.aliases:
            aliases[alias] = canonical
    return aliases


BACKEND_ALIASES = _build_alias_map()


def resolve_backend_name(value: str) -> str:
    normalized = (value or "").strip().lower()
    canonical = BACKEND_ALIASES.get(normalized)
    if not canonical:
        supported = ", ".join(sorted(BACKEND_REGISTRY))
        raise ValueError(f"Unsupported IMAGE_BACKEND='{value}'. Supported: {supported}")
    return canonical


def import_backend(canonical_name: str):
    spec = BACKEND_REGISTRY[canonical_name]
    return importlib.import_module(f"providers.{spec.module_name}")
```

Keep `skills/detail-flow-use-image-api/provider_common.py` identical to the existing `image-gen-use-api` version.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_registry.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_provider_common.py" -v
```

Expected: PASS for registry and provider-common tests.

- [ ] **Step 5: Commit**

```bash
git add tests/detail_flow_use_image_api/test_registry.py tests/detail_flow_use_image_api/test_provider_common.py skills/detail-flow-use-image-api/registry.py skills/detail-flow-use-image-api/provider_common.py
git commit -m "feat: add detail-flow image api backend registry"
```

### Task 3: Copy the provider adapters and backend configuration docs

**Files:**
- Create: `tests/detail_flow_use_image_api/test_provider_files.py`
- Create: `skills/detail-flow-use-image-api/.env.example`
- Create: `skills/detail-flow-use-image-api/providers/__init__.py`
- Create: `skills/detail-flow-use-image-api/providers/openai.py`
- Create: `skills/detail-flow-use-image-api/providers/gemini.py`
- Create: `skills/detail-flow-use-image-api/providers/openrouter.py`
- Create: `skills/detail-flow-use-image-api/providers/qwen.py`
- Create: `skills/detail-flow-use-image-api/providers/zhipu.py`
- Create: `skills/detail-flow-use-image-api/providers/volcengine.py`
- Create: `skills/detail-flow-use-image-api/providers/minimax.py`
- Create: `skills/detail-flow-use-image-api/providers/stability.py`
- Create: `skills/detail-flow-use-image-api/providers/bfl.py`
- Create: `skills/detail-flow-use-image-api/providers/ideogram.py`
- Create: `skills/detail-flow-use-image-api/providers/siliconflow.py`
- Create: `skills/detail-flow-use-image-api/providers/fal.py`
- Create: `skills/detail-flow-use-image-api/providers/replicate.py`
- Create: `skills/detail-flow-use-image-api/providers/modelscope.py`

- [ ] **Step 1: Write the failing smoke test**

Create `tests/detail_flow_use_image_api/test_provider_files.py`:

```python
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
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_provider_files.py" -v
```

Expected: FAIL because the provider package and `.env.example` do not exist yet.

- [ ] **Step 3: Copy the providers and example environment file into the new skill**

Run:

```powershell
New-Item -ItemType Directory -Force "skills/detail-flow-use-image-api/providers" | Out-Null
Copy-Item "skills/image-gen-use-api/.env.example" "skills/detail-flow-use-image-api/.env.example"
Copy-Item "skills/image-gen-use-api/providers/__init__.py" "skills/detail-flow-use-image-api/providers/__init__.py"
Copy-Item "skills/image-gen-use-api/providers/*.py" "skills/detail-flow-use-image-api/providers/"
```

After copying, do a quick spot check that the modules keep local imports such as `from provider_common import ...` and do not import `skills.image-gen-use-api` by path.

- [ ] **Step 4: Run the smoke test to verify it passes**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_provider_files.py" -v
```

Expected: PASS, confirming that all expected provider files are present and the new skill owns its backend adapters locally.

- [ ] **Step 5: Commit**

```bash
git add tests/detail_flow_use_image_api/test_provider_files.py skills/detail-flow-use-image-api/.env.example skills/detail-flow-use-image-api/providers
git commit -m "feat: add detail-flow image api providers"
```

### Task 4: Build the dedicated CLI entrypoint for masters and slice batches

**Files:**
- Create: `tests/detail_flow_use_image_api/test_cli_single.py`
- Create: `tests/detail_flow_use_image_api/test_cli_batch.py`
- Create: `skills/detail-flow-use-image-api/detail_flow_use_image_api.py`

- [ ] **Step 1: Write the failing orchestration tests**

Create `tests/detail_flow_use_image_api/test_cli_single.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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


if __name__ == "__main__":
    unittest.main()
```

Create `tests/detail_flow_use_image_api/test_cli_batch.py`:

```python
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
```

- [ ] **Step 2: Run the orchestration tests to verify they fail**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_cli_single.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_cli_batch.py" -v
```

Expected: FAIL because `detail_flow_use_image_api.py` does not exist yet.

- [ ] **Step 3: Implement the dedicated CLI entrypoint**

Start by copying the existing entrypoint:

```powershell
Copy-Item "skills/image-gen-use-api/image_gen_use_api.py" "skills/detail-flow-use-image-api/detail_flow_use_image_api.py"
```

Replace `skills/detail-flow-use-image-api/detail_flow_use_image_api.py` with:

```python
from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import threading
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from config import load_prefixed_env_file, validate_no_deprecated_image_keys
from manifest import RETRYABLE_STATUSES, build_single_item_manifest, load_manifest, save_manifest
from provider_common import is_rate_limit_error
from project_paths import create_project_paths
from registry import import_backend, resolve_backend_name


IMAGE_ENV_PREFIXES = (
    "IMAGE_",
    "GEMINI_",
    "OPENAI_",
    "MINIMAX_",
    "STABILITY_",
    "BFL_",
    "IDEOGRAM_",
    "QWEN_",
    "DASHSCOPE_",
    "ZHIPU_",
    "BIGMODEL_",
    "VOLCENGINE_",
    "ARK_",
    "MODELSCOPE_",
    "SILICONFLOW_",
    "FAL_",
    "REPLICATE_",
    "OPENROUTER_",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a detail-flow master image or run a slice manifest batch."
    )
    parser.add_argument("prompt", nargs="?", help="Prompt text for single-image mode")
    parser.add_argument("--manifest", help="Path to image_prompts.json for batch mode")
    parser.add_argument("--topic-hint", default="", help="Topic hint for project folder naming")
    parser.add_argument("--aspect-ratio", default="1:1")
    parser.add_argument("--image-size", default="1K")
    parser.add_argument("--filename", default="image.png")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--model", default="")
    return parser


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _safe_env_path() -> Path | None:
    workspace_root = _workspace_root()
    candidates = [
        workspace_root / ".env",
        SCRIPT_DIR / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _topic_for_single(args: argparse.Namespace) -> str:
    return args.topic_hint.strip() or (args.prompt or "detail-flow-image")


def _resolve_concurrency() -> int:
    raw = os.environ.get("IMAGE_CONCURRENCY", "3").strip()
    return max(1, int(raw)) if raw.isdigit() else 3


def _prepare_single_output(args: argparse.Namespace):
    if args.output_dir:
        images_dir = Path(args.output_dir).resolve()
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = images_dir / "image_prompts.json"
        return images_dir, manifest_path, images_dir.parent.name or "detail-flow-image"

    paths = create_project_paths(_workspace_root(), _topic_for_single(args))
    return paths.images_dir, paths.manifest_path, paths.project_slug


def _run_manifest_items(manifest: dict, manifest_path: Path, backend, output_dir: Path) -> dict:
    items = manifest["items"]
    queue = [index for index, item in enumerate(items) if item["status"] in RETRYABLE_STATUSES]
    skipped = len(items) - len(queue)
    current = _resolve_concurrency()
    ok = 0
    failed = 0
    state_lock = threading.Lock()

    def _one(index: int):
        item = items[index]
        try:
            saved_path = backend.generate(
                prompt=item["prompt"],
                aspect_ratio=item["aspect_ratio"],
                image_size=item.get("image_size", "1K"),
                output_dir=str(output_dir),
                filename=item["filename"],
                model=item.get("model"),
            )
            return index, saved_path, None
        except Exception as exc:
            return index, None, exc

    while queue:
        batch_size = min(current, len(queue))
        batch = queue[:batch_size]
        queue = queue[batch_size:]
        rate_limited = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as pool:
            futures = [pool.submit(_one, index) for index in batch]
            for future in concurrent.futures.as_completed(futures):
                index, saved_path, exc = future.result()
                item = items[index]
                with state_lock:
                    if exc is None:
                        item["status"] = "Generated"
                        item.pop("last_error", None)
                        item["output_path"] = saved_path
                        ok += 1
                    elif is_rate_limit_error(exc):
                        rate_limited = True
                        queue.append(index)
                    else:
                        item["status"] = "Failed"
                        item["last_error"] = str(exc)[:500]
                        failed += 1
                    save_manifest(manifest_path, manifest)

        if rate_limited and current > 1:
            current = max(1, current // 2)
            time.sleep(10)
        elif queue:
            time.sleep(2)

    return {"ok": ok, "failed": failed, "skipped": skipped}


def run_single(args: argparse.Namespace) -> dict:
    if not args.prompt:
        raise ValueError("Single-image mode requires a prompt.")

    validate_no_deprecated_image_keys(dict(os.environ))
    load_prefixed_env_file(IMAGE_ENV_PREFIXES, env_path=_safe_env_path())

    backend_name = resolve_backend_name(os.environ.get("IMAGE_BACKEND", ""))
    backend = import_backend(backend_name)

    images_dir, manifest_path, project_slug = _prepare_single_output(args)
    manifest = build_single_item_manifest(
        project_slug=project_slug,
        prompt=args.prompt,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        filename=args.filename,
    )
    if args.model:
        manifest["items"][0]["model"] = args.model
    save_manifest(manifest_path, manifest)

    item = manifest["items"][0]
    saved_path = backend.generate(
        prompt=item["prompt"],
        aspect_ratio=item["aspect_ratio"],
        image_size=item.get("image_size", "1K"),
        output_dir=str(images_dir),
        filename=item["filename"],
        model=item.get("model"),
    )

    item["status"] = "Generated"
    item["output_path"] = saved_path
    save_manifest(manifest_path, manifest)

    return {
        "mode": "single",
        "backend": backend_name,
        "output_path": saved_path,
        "manifest_path": str(manifest_path),
    }


def run_batch(args: argparse.Namespace) -> dict:
    validate_no_deprecated_image_keys(dict(os.environ))
    load_prefixed_env_file(IMAGE_ENV_PREFIXES, env_path=_safe_env_path())

    backend_name = resolve_backend_name(os.environ.get("IMAGE_BACKEND", ""))
    backend = import_backend(backend_name)

    manifest_path = Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    summary = _run_manifest_items(manifest, manifest_path, backend, manifest_path.parent)
    return {
        "mode": "batch",
        "backend": backend_name,
        "manifest_path": str(manifest_path),
        **summary,
    }


def main(argv: list[str] | None = None) -> dict:
    args = build_parser().parse_args(argv)
    if args.manifest:
        return run_batch(args)
    return run_single(args)


if __name__ == "__main__":
    result = main()
    print(result)
```

- [ ] **Step 4: Run the orchestration tests to verify they pass**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_cli_single.py" -v
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_cli_batch.py" -v
```

Expected: PASS, including the custom `--output-dir`, `--filename`, and batch status write-back behavior.

- [ ] **Step 5: Commit**

```bash
git add tests/detail_flow_use_image_api/test_cli_single.py tests/detail_flow_use_image_api/test_cli_batch.py skills/detail-flow-use-image-api/detail_flow_use_image_api.py
git commit -m "feat: add detail-flow image api cli"
```

### Task 5: Fork the detail-flow documents and make API execution explicit

**Files:**
- Create: `tests/detail_flow_use_image_api/test_docs_smoke.py`
- Create: `skills/detail-flow-use-image-api/SKILL.md`
- Create: `skills/detail-flow-use-image-api/README.md`
- Create: `skills/detail-flow-use-image-api/references/detail-page-patterns.md`
- Create: `skills/detail-flow-use-image-api/agents/openai.yaml`

- [ ] **Step 1: Write the failing documentation smoke test**

Create `tests/detail_flow_use_image_api/test_docs_smoke.py`:

```python
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
```

- [ ] **Step 2: Run the documentation smoke test to verify it fails**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_docs_smoke.py" -v
```

Expected: FAIL because the new markdown and YAML files do not exist yet.

- [ ] **Step 3: Fork the detail-flow docs and make the API-backed workflow explicit**

Copy the source files first:

```powershell
New-Item -ItemType Directory -Force "skills/detail-flow-use-image-api/references" | Out-Null
New-Item -ItemType Directory -Force "skills/detail-flow-use-image-api/agents" | Out-Null
Copy-Item "skills/detail-flow/SKILL.md" "skills/detail-flow-use-image-api/SKILL.md"
Copy-Item "skills/detail-flow/README.md" "skills/detail-flow-use-image-api/README.md"
Copy-Item "skills/detail-flow/references/detail-page-patterns.md" "skills/detail-flow-use-image-api/references/detail-page-patterns.md"
Copy-Item "skills/detail-flow/agents/openai.yaml" "skills/detail-flow-use-image-api/agents/openai.yaml"
```

Then make these exact edits.

At the top of `skills/detail-flow-use-image-api/SKILL.md`, replace the frontmatter with:

```markdown
---
name: detail-flow-use-image-api
description: Build, plan, audit, and deliver product detail pages and long ecommerce image sets while using explicit API-backed image generation through the local `detail_flow_use_image_api.py` entrypoint.
---
```

Add this paragraph near the top of `skills/detail-flow-use-image-api/SKILL.md` after the overview:

```markdown
This variant keeps the `detail-flow` workflow but requires explicit local API execution for every image-generation step. Do not switch to another image skill at runtime. Use `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py ...` for single-image masters or targeted reruns, and use `--manifest` for multi-slice batches.
```

In the execution contract and image-generation workflow sections, make these wording changes:

```markdown
- whenever the workflow says to generate a `1:3` master, explicitly call `detail_flow_use_image_api.py` in single-image mode
- whenever the workflow says to generate the first two slices or the remaining slices, explicitly call `detail_flow_use_image_api.py --manifest <path>` or run single-image calls when only one slice is being repaired
- use `IMAGE_BACKEND` plus provider-specific credentials from the environment or `.env`
- write single-image outputs and manifests under `project/<topic-slug>/images/` unless the workflow intentionally supplies `--output-dir` to keep a master or repair inside an existing slice folder
```

In `skills/detail-flow-use-image-api/references/detail-page-patterns.md`, update the image-generation output guidance so the operational lines read like this:

```markdown
- For image-generation tasks, write a master long-page prompt first, then execute `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "<prompt>" --aspect-ratio "1:3" --filename "product_master_1x3.png"` for the continuity master when needed.
- For final slices, create `image_prompts.json` in the target `images/` folder and execute `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/<topic-slug>/images/image_prompts.json"`.
```

Replace `skills/detail-flow-use-image-api/agents/openai.yaml` with:

```yaml
interface:
  display_name: "DetailFlow Use Image API"
  short_description: "Plan, generate, audit, and deliver ecommerce detail pages with explicit image API execution."
  default_prompt: "Use $detail-flow-use-image-api to create an 8-screen ecommerce detail page from my product image and style reference using explicit IMAGE_BACKEND-driven image generation."
```

Replace `skills/detail-flow-use-image-api/README.md` with:

```markdown
# DetailFlow Use Image API

`detail-flow-use-image-api` is a standalone fork of `detail-flow` that keeps the blueprint-first, audit-heavy ecommerce page workflow but uses explicit local image API execution for masters and slice batches.

## Core behavior

- Keep the two user approval gates from `detail-flow`
- Preserve the `1:3` master plus `9:21` slice workflow
- Use `IMAGE_BACKEND` plus provider-specific credentials
- Run single-image generation through `detail_flow_use_image_api.py`
- Run slice batches through `detail_flow_use_image_api.py --manifest`

## Configuration

Set `IMAGE_BACKEND` and provider-specific credentials in the current environment or `.env`. See `.env.example` for the full backend matrix.

## Examples

```bash
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "A polished 1:3 product continuity master" --aspect-ratio "1:3" --filename "product_master_1x3.png" --topic-hint "smart fan"
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/smart-fan/images/image_prompts.json"
```

## Source workflow

This skill is based on `detail-flow`, but it is independently runnable and does not import `image-gen-use-api` at runtime.
```

- [ ] **Step 4: Run the documentation smoke test to verify it passes**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_docs_smoke.py" -v
```

Expected: PASS, confirming that the new skill is self-contained and explicitly documents API-backed generation.

- [ ] **Step 5: Commit**

```bash
git add tests/detail_flow_use_image_api/test_docs_smoke.py skills/detail-flow-use-image-api/SKILL.md skills/detail-flow-use-image-api/README.md skills/detail-flow-use-image-api/references/detail-page-patterns.md skills/detail-flow-use-image-api/agents/openai.yaml
git commit -m "feat: fork detail-flow for explicit image api use"
```

### Task 6: Run the full verification pass and prepare the skill for execution

**Files:**
- Modify: `skills/detail-flow-use-image-api/`
- Modify: `tests/detail_flow_use_image_api/`

- [ ] **Step 1: Run the full targeted test suite**

Run:

```bash
python -m unittest discover -s tests/detail_flow_use_image_api -p "test_*.py" -v
```

Expected: PASS for all tests created in Tasks 1 through 5.

- [ ] **Step 2: Run the CLI help command and verify the new flags are visible**

Run:

```bash
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --help
```

Expected: the help output includes `--manifest`, `--filename`, `--output-dir`, `--aspect-ratio`, `--image-size`, and `--model`.

- [ ] **Step 3: Perform a manual doc spot-check against the spec**

Check these exact points by reading the files side by side:

```text
docs/superpowers/specs/2026-06-23-detail-flow-use-image-api-design.md
skills/detail-flow-use-image-api/SKILL.md
skills/detail-flow-use-image-api/README.md
skills/detail-flow-use-image-api/references/detail-page-patterns.md
```

Confirm all of the following:

- the two standard approval gates are still present
- the workflow still goes blueprint -> master -> first two slices -> preview -> remaining slices
- every image-generation stage points to explicit local script execution
- the docs never tell the agent to switch to `image-gen-use-api` at runtime
- the backend policy still centers on `IMAGE_BACKEND`

- [ ] **Step 4: Commit the finished skill**

```bash
git add skills/detail-flow-use-image-api tests/detail_flow_use_image_api
git commit -m "feat: add detail-flow-use-image-api skill"
```
