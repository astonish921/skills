from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from provider_common import MAX_RETRIES, download_image, http_error, is_rate_limit_error, require_api_key, retry_delay


DEFAULT_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v3/generate"
DEFAULT_MODEL = "ideogram-v3"
ASPECT_RATIO_MAP = {
    "1:1": "1x1",
    "2:3": "2x3",
    "3:2": "3x2",
    "3:4": "3x4",
    "4:3": "4x3",
    "4:5": "4x5",
    "5:4": "5x4",
    "9:16": "9x16",
    "16:9": "16x9",
    "21:9": "21x9",
}
IMAGE_SIZE_TO_SPEED = {"512px": "TURBO", "1K": "DEFAULT", "2K": "QUALITY", "4K": "QUALITY"}


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
        "IDEOGRAM_API_KEY",
        message="No API key found. Set IDEOGRAM_API_KEY in the current environment or a .env file.",
    )
    base_url = os.environ.get("IDEOGRAM_BASE_URL") or DEFAULT_ENDPOINT
    resolved_model = (model or os.environ.get("IDEOGRAM_MODEL") or DEFAULT_MODEL).strip().lower()
    if resolved_model not in {"ideogram-v3", "v3"}:
        raise ValueError(
            f"Unsupported Ideogram model '{resolved_model}'. Supported: ['ideogram-v3', 'v3']"
        )
    mapped_ratio = ASPECT_RATIO_MAP.get(aspect_ratio)
    if not mapped_ratio:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for Ideogram backend. Supported: {sorted(ASPECT_RATIO_MAP)}"
        )
    files = {
        "prompt": (None, prompt),
        "aspect_ratio": (None, mapped_ratio),
        "rendering_speed": (None, IMAGE_SIZE_TO_SPEED.get(image_size, "DEFAULT")),
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                base_url,
                headers={"Api-Key": api_key},
                files=files,
                timeout=300,
            )
            if response.status_code != 200:
                raise http_error(response, "Ideogram generation")
            data = response.json()
            image_url = ((data.get("data") or [{}])[0]).get("url")
            if not image_url:
                raise RuntimeError(f"Ideogram response missing image URL: {data}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
