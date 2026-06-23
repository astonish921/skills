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
from manifest import (
    RETRYABLE_STATUSES,
    build_single_item_manifest,
    load_manifest,
    save_manifest,
)
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
        description="Generate one image or run a manifest batch."
    )
    parser.add_argument("prompt", nargs="?", help="Prompt text for single-image mode")
    parser.add_argument("--manifest", help="Path to image_prompts.json for batch mode")
    parser.add_argument(
        "--topic-hint", default="", help="Host-supplied topic hint for folder naming"
    )
    parser.add_argument("--aspect-ratio", default="1:1")
    parser.add_argument("--image-size", default="1K")
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
    return candidates[0]


def _topic_for_single(args: argparse.Namespace) -> str:
    return args.topic_hint.strip() or (args.prompt or "image gen")


def _resolve_concurrency() -> int:
    raw = os.environ.get("IMAGE_CONCURRENCY", "3").strip()
    return max(1, int(raw)) if raw.isdigit() else 3


def _run_manifest_items(
    manifest: dict,
    manifest_path: Path,
    backend,
    output_dir: Path,
) -> dict:
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
        except Exception as exc:  # noqa: BLE001
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

    return {
        "ok": ok,
        "failed": failed,
        "skipped": skipped,
    }


def run_single(args: argparse.Namespace) -> dict:
    if not args.prompt:
        raise ValueError("Single-image mode requires a prompt.")

    validate_no_deprecated_image_keys(dict(os.environ))
    load_prefixed_env_file(IMAGE_ENV_PREFIXES, env_path=_safe_env_path())

    backend_name = resolve_backend_name(os.environ.get("IMAGE_BACKEND", ""))
    backend = import_backend(backend_name)

    paths = create_project_paths(_workspace_root(), _topic_for_single(args))
    manifest = build_single_item_manifest(
        project_slug=paths.project_slug,
        prompt=args.prompt,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
    )
    save_manifest(paths.manifest_path, manifest)

    item = manifest["items"][0]
    saved_path = backend.generate(
        prompt=item["prompt"],
        aspect_ratio=item["aspect_ratio"],
        image_size=item["image_size"],
        output_dir=str(paths.images_dir),
        filename=item["filename"],
        model=None,
    )

    item["status"] = "Generated"
    save_manifest(paths.manifest_path, manifest)

    return {
        "mode": "single",
        "backend": backend_name,
        "output_path": saved_path,
        "manifest_path": str(paths.manifest_path),
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
