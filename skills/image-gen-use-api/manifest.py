from __future__ import annotations

import json
from datetime import date
from pathlib import Path


VALID_STATUSES = {"Pending", "Generated", "Failed", "Needs-Manual"}
RETRYABLE_STATUSES = {"Pending", "Failed"}
REQUIRED_ITEM_FIELDS = ("filename", "prompt", "aspect_ratio", "status")


def build_single_item_manifest(
    project_slug: str,
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    filename: str = "image.png",
) -> dict:
    return {
        "project": project_slug,
        "generated_at": str(date.today()),
        "items": [
            {
                "filename": filename,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "status": "Pending",
            }
        ],
    }


def validate_manifest(data: dict, path_label: str) -> dict:
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"{path_label}: 'items' must be a non-empty array")

    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{path_label}: items[{index}] must be an object")
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item:
                raise ValueError(f"{path_label}: items[{index}] missing required field '{field}'")
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(
                    f"{path_label}: items[{index}].{field} must be a non-empty string"
                )
        if item["status"] not in VALID_STATUSES:
            raise ValueError(
                f"{path_label}: items[{index}].status '{item['status']}' is invalid"
            )
        if item["filename"] in seen:
            raise ValueError(f"{path_label}: duplicate filename '{item['filename']}'")
        seen.add(item["filename"])
    return data


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a JSON object")
    return validate_manifest(data, str(path))


def save_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
