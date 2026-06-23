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


DEFAULT_BASE_URL = "https://api.replicate.com/v1"
DEFAULT_MODEL = "black-forest-labs/flux-1.1-pro"
VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:4", "4:3", "3:2", "2:3", "4:5", "5:4", "21:9"]


def _split_model(model: str) -> tuple[str, str]:
    parts = [part for part in model.strip().split("/") if part]
    if len(parts) != 2:
        raise ValueError(f"Replicate model must be in 'owner/name' format, got '{model}'.")
    return parts[0], parts[1]


def _extract_output_url(payload: dict) -> str | None:
    output = payload.get("output")
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        return first.get("url") if isinstance(first, dict) else first
    if isinstance(output, dict):
        return output.get("url")
    return None


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
        "REPLICATE_API_KEY",
        "REPLICATE_API_TOKEN",
        message="No API key found. Set REPLICATE_API_KEY or REPLICATE_API_TOKEN in the current environment or a .env file.",
    )
    base_url = os.environ.get("REPLICATE_BASE_URL") or DEFAULT_BASE_URL
    resolved_model = model or os.environ.get("REPLICATE_MODEL") or DEFAULT_MODEL
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for Replicate backend. Supported: {VALID_ASPECT_RATIOS}"
        )
    owner, name = _split_model(resolved_model)
    payload = {"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": "png"}}

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/models/{owner}/{name}/predictions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "wait=60",
                },
                json=payload,
                timeout=180,
            )
            if response.status_code not in (200, 201):
                raise http_error(response, "Replicate generation request")
            data = response.json()
            status = str(data.get("status", "")).lower()
            if status != "succeeded":
                poll_url = ((data.get("urls") or {}).get("get")) or (
                    f"{base_url.rstrip('/')}/predictions/{data['id']}" if data.get("id") else None
                )
                if not poll_url:
                    raise RuntimeError(f"Replicate response missing poll URL: {data}")
                data = poll_json(
                    poll_url,
                    {"Authorization": f"Bearer {api_key}"},
                    status_label="status",
                    ready_values=["succeeded"],
                    failed_values=["failed", "canceled"],
                )
            image_url = _extract_output_url(data)
            if not image_url:
                raise RuntimeError(f"Replicate response missing output URL: {data}")
            return str(download_image(image_url, Path(output_dir or ".") / filename))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
