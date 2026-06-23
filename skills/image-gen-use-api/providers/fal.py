from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from provider_common import MAX_RETRIES, download_image, http_error, is_rate_limit_error, require_api_key, retry_delay


DEFAULT_ENDPOINT = "https://fal.run"
DEFAULT_MODEL = "fal-ai/imagen3/fast"
VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:4", "4:3"]


def generate(
    prompt: str,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    output_dir: str | None = None,
    filename: str = "image.png",
    model: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> str:
    del image_size
    api_key = require_api_key(
        "FAL_KEY",
        "FAL_API_KEY",
        message="No API key found. Set FAL_KEY or FAL_API_KEY in the current environment or a .env file.",
    )
    base_url = (os.environ.get("FAL_BASE_URL") or DEFAULT_ENDPOINT).rstrip("/")
    resolved_model = model or os.environ.get("FAL_MODEL") or DEFAULT_MODEL
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for fal backend. Supported: {VALID_ASPECT_RATIOS}"
        )
    url = base_url if base_url.endswith(resolved_model) else f"{base_url}/{resolved_model}"
    payload = {"prompt": prompt, "aspect_ratio": aspect_ratio, "num_images": 1}

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            if response.status_code != 200:
                raise http_error(response, "fal image generation")
            data = response.json()
            image_url = ((data.get("images") or [{}])[0]).get("url")
            if not image_url:
                raise RuntimeError(f"fal response missing image URL: {data}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
