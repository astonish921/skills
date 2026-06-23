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
        Path.home() / ".image-gen-use-api" / ".env",
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
