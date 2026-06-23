# image-gen-use-api

`image-gen-use-api` is a self-contained image generation skill with a small CLI, provider registry, manifest helpers, and backend adapters.

## Install dependencies

```bash
pip install requests Pillow
pip install google-genai
```

`google-genai` is only required for `IMAGE_BACKEND=gemini`.

## Configuration

Set provider configuration in the process environment, or place a `.env` file in the workspace root or `skills/image-gen-use-api/`.

The CLI reads `IMAGE_BACKEND` plus provider-specific keys such as:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `QWEN_API_KEY` or `DASHSCOPE_API_KEY`
- `ZHIPU_API_KEY` or `BIGMODEL_API_KEY`
- `VOLCENGINE_API_KEY` or `ARK_API_KEY`
- `REPLICATE_API_KEY` or `REPLICATE_API_TOKEN`

Process environment values take precedence over `.env` values.

Do not use deprecated global keys:

- `IMAGE_API_KEY`
- `IMAGE_MODEL`
- `IMAGE_BASE_URL`

See `.env.example` for the full backend matrix.

## Single image

Single-image mode is the default when you pass a prompt.

```bash
python skills/image-gen-use-api/image_gen_use_api.py "A clean blue SaaS hero image" --topic-hint "saas hero"
python skills/image-gen-use-api/image_gen_use_api.py "A bold product launch poster" --topic-hint "launch" --aspect-ratio "16:9" --image-size "1K"
```

This creates a new project folder and writes both the generated image and manifest under:

```text
project/<topic-slug>/images/
```

The manifest filename is:

```text
project/<topic-slug>/images/image_prompts.json
```

## Batch manifest

Batch mode runs when you provide `--manifest`.

```bash
python skills/image-gen-use-api/image_gen_use_api.py --manifest "project/saas-hero/images/image_prompts.json"
```

The manifest must contain an `items` array with per-image fields such as `filename`, `prompt`, `aspect_ratio`, and `status`. The batch runner retries `Pending` and `Failed` items, writes status updates back into `image_prompts.json`, and uses `IMAGE_CONCURRENCY` to control worker count.

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

## Smoke test examples

```bash
set IMAGE_BACKEND=openai
set OPENAI_API_KEY=your-key
python skills/image-gen-use-api/image_gen_use_api.py "A minimal navy product poster" --topic-hint "openai smoke"

set IMAGE_BACKEND=gemini
set GEMINI_API_KEY=your-key
python skills/image-gen-use-api/image_gen_use_api.py "A minimal navy product poster" --topic-hint "gemini smoke"
```
