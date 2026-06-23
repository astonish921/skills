from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests

from provider_common import (
    MAX_RETRIES,
    detect_image_extension,
    http_error,
    is_rate_limit_error,
    normalize_image_size,
    require_api_key,
    retry_delay,
    save_image_bytes,
)


DEFAULT_ENDPOINT = "https://api.minimaxi.com/v1/image_generation"
DEFAULT_MODEL = "image-01"
SIZE_MAP = {
    "1K": {"1:1": (1024, 1024), "16:9": (1280, 720), "9:16": (720, 1280)},
    "512px": {"1:1": (512, 512), "16:9": (640, 360), "9:16": (360, 640)},
    "2K": {"1:1": (2048, 2048), "16:9": (2048, 1152), "9:16": (1152, 2048)},
    "4K": {"1:1": (2048, 2048), "16:9": (2048, 1152), "9:16": (1152, 2048)},
}


def _resolve_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/image_generation"):
        return base
    if base.endswith("/v1"):
        return base + "/image_generation"
    return base + "/v1/image_generation"


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
        "MINIMAX_API_KEY",
        message="No API key found. Set MINIMAX_API_KEY in the current environment or a .env file.",
    )
    base_url = _resolve_url(os.environ.get("MINIMAX_BASE_URL") or DEFAULT_ENDPOINT)
    resolved_model = model or os.environ.get("MINIMAX_MODEL") or DEFAULT_MODEL
    width, height = SIZE_MAP[normalize_image_size(image_size)][aspect_ratio]
    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "response_format": "base64",
        "n": 1,
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            if response.status_code != 200:
                raise http_error(response, "MiniMax image generation")
            data = response.json()
            if (data.get("base_resp") or {}).get("status_code") not in (None, 0, "0"):
                raise RuntimeError(f"MiniMax image generation failed: {data}")
            image_base64 = ((data.get("data") or {}).get("image_base64") or [None])[0]
            if not image_base64:
                raise RuntimeError(f"MiniMax response missing image data: {data}")
            image_bytes = base64.b64decode(image_base64)
            ext = detect_image_extension(image_bytes) or Path(filename).suffix or ".jpeg"
            target = Path(output_dir or ".") / Path(filename).with_suffix(ext).name
            return str(save_image_bytes(image_bytes, target))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
