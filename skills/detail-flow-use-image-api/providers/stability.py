from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from provider_common import (
    MAX_RETRIES,
    http_error,
    is_rate_limit_error,
    require_api_key,
    retry_delay,
    save_image_bytes,
)


DEFAULT_BASE_URL = "https://api.stability.ai"
DEFAULT_MODEL = "stable-image-core"
MODEL_ENDPOINTS = {
    "core": "/v2beta/stable-image/generate/core",
    "stable-image-core": "/v2beta/stable-image/generate/core",
    "ultra": "/v2beta/stable-image/generate/ultra",
    "stable-image-ultra": "/v2beta/stable-image/generate/ultra",
}
VALID_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]


def _resolve_endpoint(model: str, image_size: str, base_url: str) -> str:
    resolved_model = model or DEFAULT_MODEL
    if not model and image_size.upper() in {"2K", "4K"}:
        resolved_model = "stable-image-ultra"
    endpoint = MODEL_ENDPOINTS.get(resolved_model.lower())
    if not endpoint:
        raise ValueError(
            f"Unsupported Stability model '{resolved_model}'. Supported aliases: {sorted(MODEL_ENDPOINTS)}"
        )
    return base_url.rstrip("/") + endpoint


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
        "STABILITY_API_KEY",
        message="No API key found. Set STABILITY_API_KEY in the current environment or a .env file.",
    )
    base_url = os.environ.get("STABILITY_BASE_URL") or DEFAULT_BASE_URL
    resolved_model = model or os.environ.get("STABILITY_MODEL") or DEFAULT_MODEL
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for Stability backend. Supported: {VALID_ASPECT_RATIOS}"
        )
    url = _resolve_endpoint(resolved_model, image_size, base_url)
    payload = {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": "png"}

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
                data=payload,
                timeout=300,
            )
            if response.status_code != 200:
                raise http_error(response, "Stability generation")
            target = Path(output_dir or ".") / filename
            return str(save_image_bytes(response.content, target, response.headers.get("Content-Type")))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
