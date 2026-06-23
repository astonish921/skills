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
    require_api_key,
    retry_delay,
)


DEFAULT_ENDPOINT = "https://api.siliconflow.cn/v1/images/generations"
DEFAULT_MODEL = "Qwen/Qwen-Image"
SIZE_MAP = {
    "1K": {"1:1": "1328x1328", "16:9": "1664x928", "9:16": "928x1664"},
    "512px": {"1:1": "1024x1024", "16:9": "1664x928", "9:16": "928x1664"},
    "2K": {"1:1": "2048x2048", "16:9": "2048x1152", "9:16": "1152x2048"},
    "4K": {"1:1": "2048x2048", "16:9": "2048x1152", "9:16": "1152x2048"},
}


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
        "SILICONFLOW_API_KEY",
        message="No API key found. Set SILICONFLOW_API_KEY in the current environment or a .env file.",
    )
    base_url = os.environ.get("SILICONFLOW_BASE_URL") or DEFAULT_ENDPOINT
    resolved_model = model or os.environ.get("SILICONFLOW_MODEL") or DEFAULT_MODEL
    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "image_size": SIZE_MAP[normalize_image_size(image_size)][aspect_ratio],
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
                raise http_error(response, "SiliconFlow image generation")
            data = response.json()
            image_url = ((data.get("images") or [{}])[0]).get("url")
            if not image_url:
                raise RuntimeError(f"SiliconFlow response missing image URL: {data}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
