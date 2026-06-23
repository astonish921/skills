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
