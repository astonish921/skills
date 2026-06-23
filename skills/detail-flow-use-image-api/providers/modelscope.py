from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from provider_common import (
    MAX_RETRIES,
    download_image,
    http_error,
    is_rate_limit_error,
    normalize_image_size,
    poll_json,
    require_api_key,
    retry_delay,
)


DEFAULT_ENDPOINT = "https://api-inference.modelscope.cn"
DEFAULT_MODEL = "Tongyi-MAI/Z-Image-Turbo"
SIZE_MAP = {
    "1K": {"1:1": "1280*1280", "3:4": "960*1280", "4:3": "1280*960", "9:16": "576*1024", "16:9": "1024*576"},
    "512px": {"1:1": "1024*1024", "3:4": "768*1024", "4:3": "1024*768", "9:16": "576*1024", "16:9": "1024*576"},
    "2K": {"1:1": "2048*2048", "3:4": "1536*2048", "4:3": "2048*1536", "9:16": "1152*2048", "16:9": "2048*1152"},
    "4K": {"1:1": "2048*2048", "3:4": "1920*2560", "4:3": "2560*1920", "9:16": "1728*3072", "16:9": "3072*1728"},
}


def _resolve_base(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base.removesuffix("/v1") if base.endswith("/v1") else base


def generate(
    prompt: str,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    output_dir: str | None = None,
    filename: str = "image.png",
    model: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> str:
    api_key = require_api_key(
        "MODELSCOPE_API_KEY",
        message="No API key found. Set MODELSCOPE_API_KEY in the current environment or a .env file.",
    )
    base_url = _resolve_base(os.environ.get("MODELSCOPE_BASE_URL") or DEFAULT_ENDPOINT)
    resolved_model = model or os.environ.get("MODELSCOPE_MODEL") or DEFAULT_MODEL
    size = SIZE_MAP[normalize_image_size(image_size)][aspect_ratio].replace("*", "x")
    payload = {"model": resolved_model, "prompt": prompt, "size": size}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url}/v1/images/generations",
                headers={**headers, "X-ModelScope-Async-Mode": "true"},
                json=payload,
                timeout=300,
            )
            if response.status_code != 200:
                raise http_error(response, "ModelScope image generation")
            task_id = response.json()["task_id"]
            data = poll_json(
                f"{base_url}/v1/tasks/{task_id}",
                {**headers, "X-ModelScope-Task-Type": "image_generation"},
                status_label="task_status",
                ready_values=["SUCCEED"],
                failed_values=["FAILED"],
            )
            image_url = data["output_images"][0]
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
