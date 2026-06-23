from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from provider_common import MAX_RETRIES, is_rate_limit_error, require_api_key, retry_delay, save_image_bytes


DEFAULT_MODEL = "gemini-3.1-flash-image-preview"


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
        "GEMINI_API_KEY",
        message="No API key found. Set GEMINI_API_KEY in the current environment or a .env file.",
    )

    from google import genai

    sdk_types = sys.modules.get("google.genai.types")
    if sdk_types is None:
        from google.genai import types as sdk_types

    resolved_model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    base_url = os.environ.get("GEMINI_BASE_URL")
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["http_options"] = {"base_url": base_url}
    client = genai.Client(**client_kwargs)

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            config = sdk_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=sdk_types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            )
            inline_data = None
            for chunk in client.models.generate_content_stream(
                model=resolved_model,
                contents=[prompt],
                config=config,
            ):
                for part in getattr(chunk, "parts", []) or []:
                    if getattr(part, "inline_data", None) is not None:
                        inline_data = part.inline_data
            if inline_data is None:
                raise RuntimeError("No image was generated. The server may have refused the request.")
            target = Path(output_dir or ".") / filename
            return str(
                save_image_bytes(
                    inline_data.data,
                    target,
                    getattr(inline_data, "mime_type", None),
                )
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_delay(attempt, rate_limited=is_rate_limit_error(exc)))
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
