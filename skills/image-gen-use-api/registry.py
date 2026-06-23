from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSpec:
    module_name: str
    default_model: str
    aliases: tuple[str, ...] = ()


BACKEND_REGISTRY: dict[str, BackendSpec] = {
    "openai": BackendSpec("openai", "gpt-image-2", ("openai-compatible", "openai_compatible")),
    "gemini": BackendSpec("gemini", "gemini-3.1-flash-image-preview", ("google",)),
    "qwen": BackendSpec("qwen", "qwen-image-2.0-pro", ("dashscope",)),
    "zhipu": BackendSpec("zhipu", "glm-image", ("bigmodel", "glm")),
    "volcengine": BackendSpec("volcengine", "doubao-seedream-4-5-251128", ("ark", "doubao", "seedream")),
    "minimax": BackendSpec("minimax", "image-01", ("minimaxi",)),
    "stability": BackendSpec("stability", "stable-image-core", ("stabilityai",)),
    "bfl": BackendSpec("bfl", "flux-pro-1.1-ultra", ("flux", "black-forest-labs")),
    "ideogram": BackendSpec("ideogram", "ideogram-v3"),
    "siliconflow": BackendSpec("siliconflow", "Qwen/Qwen-Image", ("silicon",)),
    "fal": BackendSpec("fal", "fal-ai/imagen3/fast", ("fal-ai",)),
    "replicate": BackendSpec("replicate", "black-forest-labs/flux-1.1-pro"),
    "openrouter": BackendSpec("openrouter", "google/gemini-3.1-flash-image-preview"),
    "modelscope": BackendSpec("modelscope", "Tongyi-MAI/Z-Image-Turbo"),
}


def _build_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, spec in BACKEND_REGISTRY.items():
        aliases[canonical] = canonical
        for alias in spec.aliases:
            aliases[alias] = canonical
    return aliases


BACKEND_ALIASES = _build_alias_map()


def resolve_backend_name(value: str) -> str:
    normalized = (value or "").strip().lower()
    canonical = BACKEND_ALIASES.get(normalized)
    if not canonical:
        supported = ", ".join(sorted(BACKEND_REGISTRY))
        raise ValueError(f"Unsupported IMAGE_BACKEND='{value}'. Supported: {supported}")
    return canonical


def import_backend(canonical_name: str):
    spec = BACKEND_REGISTRY[canonical_name]
    return importlib.import_module(f"providers.{spec.module_name}")
