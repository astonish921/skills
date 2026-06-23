from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests

from provider_common import MAX_RETRIES, is_rate_limit_error, require_api_key, retry_delay, save_image_bytes


DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


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
        "OPENROUTER_API_KEY",
        message="No API key found. Set OPENROUTER_API_KEY in the current environment or a .env file.",
    )
    resolved_model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
    base_url = os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
    payload = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": aspect_ratio, "image_size": image_size},
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            result = response.json()
            images = ((result.get("choices") or [{}])[0].get("message") or {}).get("images") or []
            url = images[0].get("image_url", {}).get("url") if images else None
            if not url or not url.startswith("data:image/"):
                raise RuntimeError("OpenRouter response missing image data URL.")
            header, encoded = url.split(",", 1)
            content_type = header.split(";", 1)[0].split(":", 1)[1]
            target = Path(output_dir or ".") / filename
            return str(save_image_bytes(base64.urlsafe_b64decode(encoded), target, content_type))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
