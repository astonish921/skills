---
name: image-gen-use-api
description: "Generate images through configured API backends. Single-image mode is the default, batch mode uses a manifest, and outputs are written under project/<topic-slug>/images/."
---

# image-gen-use-api

Use this skill when the user wants image generation through one of the configured API backends in `skills/image-gen-use-api/`.

## Behavior

- single-image mode is the default
- switch to batch mode only when the user explicitly asks for multiple images or provides a manifest path
- choose the provider from `IMAGE_BACKEND`
- load provider settings from the current environment first, then fill missing values from `.env`
- write single-image outputs under `project/<topic-slug>/images/`
- write the run manifest as `project/<topic-slug>/images/image_prompts.json`

## Supported backends

- `openai`
- `gemini`
- `qwen`
- `zhipu`
- `volcengine`
- `minimax`
- `stability`
- `bfl`
- `ideogram`
- `siliconflow`
- `fal`
- `replicate`
- `openrouter`
- `modelscope`

## Dependencies

- `requests`
- `Pillow`
- `google-genai` only when `IMAGE_BACKEND=gemini`

## Examples

```bash
python skills/image-gen-use-api/image_gen_use_api.py "A minimal tech poster" --topic-hint "Tech Poster"
python skills/image-gen-use-api/image_gen_use_api.py --manifest "project/demo/images/image_prompts.json"
```

## Configuration notes

- Use provider-specific keys such as `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY`.
- Do not use deprecated global keys such as `IMAGE_API_KEY`, `IMAGE_MODEL`, or `IMAGE_BASE_URL`.
