from __future__ import annotations

import io
import os
import time
from pathlib import Path

import requests

try:
    from PIL import Image as PILImage
except ImportError:  # pragma: no cover - exercised only when Pillow missing
    PILImage = None


MAX_RETRIES = 3
RETRY_BASE_DELAY = 10
RETRY_BACKOFF = 2

CONTENT_TYPE_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}


def normalize_image_size(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"1K", "2K", "4K"}:
        return normalized
    if normalized in {"512", "512PX"}:
        return "512px"
    return value


def detect_image_extension(image_bytes: bytes, content_type: str | None = None) -> str | None:
    if content_type:
        clean = content_type.split(";", 1)[0].strip().lower()
        if clean in CONTENT_TYPE_TO_EXT:
            return CONTENT_TYPE_TO_EXT[clean]
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return ".webp"
    return None


def save_image_bytes(image_bytes: bytes, path: Path, content_type: str | None = None) -> Path:
    actual_ext = detect_image_extension(image_bytes, content_type) or path.suffix.lower()
    if actual_ext == path.suffix.lower():
        path.write_bytes(image_bytes)
        return path
    if PILImage is None:
        raise RuntimeError("Install Pillow to convert mismatched image formats.")
    image = PILImage.open(io.BytesIO(image_bytes))
    if path.suffix.lower() in {".jpg", ".jpeg"} and image.mode in {"RGBA", "LA", "P"}:
        image = image.convert("RGB")
    image.save(path)
    return path


def download_image(url: str, path: Path, headers: dict[str, str] | None = None) -> Path:
    response = requests.get(url, headers=headers or {}, timeout=180)
    response.raise_for_status()
    return save_image_bytes(response.content, path, response.headers.get("Content-Type"))


def require_api_key(*names: str, message: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    raise ValueError(message)


def is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate" in text or "quota" in text or "resource_exhausted" in text


def retry_delay(attempt: int, *, rate_limited: bool) -> int:
    if rate_limited:
        return RETRY_BASE_DELAY * (RETRY_BACKOFF ** attempt)
    return 5


def http_error(response: requests.Response, label: str) -> RuntimeError:
    body = response.text.strip()
    if len(body) > 500:
        body = body[:500] + "..."
    return RuntimeError(f"{label} failed ({response.status_code}): {body}")


def poll_json(
    url: str,
    headers: dict[str, str],
    *,
    status_label: str,
    ready_values: list[str],
    failed_values: list[str],
    interval_seconds: float = 2.0,
    timeout_seconds: int = 300,
) -> dict:
    deadline = time.time() + timeout_seconds
    while True:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get(status_label, "")).strip()
        if status in ready_values:
            return payload
        if status in failed_values:
            raise RuntimeError(f"Polling failed with status '{status}': {payload}")
        if time.time() >= deadline:
            raise TimeoutError(f"Polling timed out after {timeout_seconds}s: {url}")
        time.sleep(interval_seconds)
