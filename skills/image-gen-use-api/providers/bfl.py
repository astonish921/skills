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
    poll_json,
    require_api_key,
    retry_delay,
)


DEFAULT_BASE_URL = "https://api.bfl.ai"
DEFAULT_MODEL = "flux-pro-1.1-ultra"
MODEL_ENDPOINTS = {
    "flux-pro-1.1": "/v1/flux-pro-1.1",
    "flux-pro-1.1-ultra": "/v1/flux-pro-1.1-ultra",
    "flux-dev": "/v1/flux-dev",
}
VALID_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
ASPECT_RATIO_TO_DIMENSIONS = {
    "1:1": (1024, 1024),
    "2:3": (1024, 1536),
    "3:2": (1536, 1024),
    "3:4": (1024, 1365),
    "4:3": (1365, 1024),
    "4:5": (1024, 1280),
    "5:4": (1280, 1024),
    "9:16": (1024, 1820),
    "16:9": (1820, 1024),
    "21:9": (2048, 878),
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
    del image_size
    api_key = require_api_key(
        "BFL_API_KEY",
        message="No API key found. Set BFL_API_KEY in the current environment or a .env file.",
    )
    base_url = os.environ.get("BFL_BASE_URL") or DEFAULT_BASE_URL
    resolved_model = (model or os.environ.get("BFL_MODEL") or DEFAULT_MODEL).strip().lower()
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for BFL backend. Supported: {VALID_ASPECT_RATIOS}"
        )
    endpoint = MODEL_ENDPOINTS.get(resolved_model)
    if not endpoint:
        raise ValueError(f"Unsupported BFL model '{resolved_model}'. Supported: {sorted(MODEL_ENDPOINTS)}")
    payload = {"prompt": prompt, "prompt_upsampling": False, "output_format": "png"}
    if resolved_model.endswith("-ultra"):
        payload["aspect_ratio"] = aspect_ratio
        payload["raw"] = False
    else:
        width, height = ASPECT_RATIO_TO_DIMENSIONS[aspect_ratio]
        payload["width"] = width
        payload["height"] = height

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}{endpoint}",
                headers={
                    "x-key": api_key,
                    "accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=180,
            )
            if response.status_code != 200:
                raise http_error(response, "BFL generation request")
            accepted = response.json()
            polling_url = accepted.get("polling_url")
            if not polling_url:
                raise RuntimeError(f"BFL response missing polling_url: {accepted}")
            result = poll_json(
                polling_url,
                {"x-key": api_key, "accept": "application/json"},
                status_label="status",
                ready_values=["Ready"],
                failed_values=["Error", "Failed", "Request Moderated", "Content Moderated"],
            )
            image_url = (result.get("result") or {}).get("sample")
            if not image_url:
                raise RuntimeError(f"BFL result missing sample URL: {result}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
