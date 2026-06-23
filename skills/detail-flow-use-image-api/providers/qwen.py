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


DEFAULT_ENDPOINT = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen-image-2.0-pro"
SIZE_MAP = {
    "1K": {"1:1": "1536*1536", "16:9": "1600*896", "9:16": "896*1600"},
    "512px": {"1:1": "1024*1024", "16:9": "1280*720", "9:16": "720*1280"},
    "2K": {"1:1": "2048*2048", "16:9": "2688*1536", "9:16": "1536*2688"},
    "4K": {"1:1": "2048*2048", "16:9": "2688*1536", "9:16": "1536*2688"},
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
        "QWEN_API_KEY",
        "DASHSCOPE_API_KEY",
        message="No API key found. Set QWEN_API_KEY or DASHSCOPE_API_KEY in the current environment or a .env file.",
    )
    base_url = os.environ.get("QWEN_BASE_URL") or DEFAULT_ENDPOINT
    resolved_model = model or os.environ.get("QWEN_MODEL") or DEFAULT_MODEL
    resolved_size = SIZE_MAP[normalize_image_size(image_size)][aspect_ratio]
    payload = {
        "model": resolved_model,
        "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
        "parameters": {"size": resolved_size, "prompt_extend": True, "watermark": False},
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
                raise http_error(response, "Qwen image generation")
            data = response.json()
            image_url = (
                (((data.get("output") or {}).get("choices") or [{}])[0].get("message") or {})
                .get("content", [{}])[0]
                .get("image")
            )
            if not image_url:
                raise RuntimeError(f"Qwen response missing image URL: {data}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
