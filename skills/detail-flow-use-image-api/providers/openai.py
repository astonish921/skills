from __future__ import annotations

import base64
import time
from pathlib import Path

import requests

from provider_common import MAX_RETRIES, is_rate_limit_error, require_api_key, retry_delay, save_image_bytes


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def _size_for_aspect_ratio(aspect_ratio: str) -> str:
    if aspect_ratio == "1:1":
        return "1024x1024"
    return "1536x1024"


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
        "OPENAI_API_KEY",
        message="No API key found. Set OPENAI_API_KEY in the current environment or a .env file.",
    )
    resolved_model = model or __import__("os").environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    base_url = __import__("os").environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "size": _size_for_aspect_ratio(aspect_ratio),
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            data = response.json().get("data") or []
            image_b64 = data[0].get("b64_json") if data else None
            if not image_b64:
                raise RuntimeError("OpenAI response missing b64_json image data.")
            target = Path(output_dir or ".") / filename
            return str(save_image_bytes(base64.b64decode(image_b64), target))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
