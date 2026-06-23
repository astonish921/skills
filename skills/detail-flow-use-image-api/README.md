# detail-flow-use-image-api

`detail-flow-use-image-api` is a standalone fork of `detail-flow` that keeps the blueprint-first, audit-heavy ecommerce page workflow but uses explicit local image API execution for masters and slice batches.

## Core behavior

- Keep the two user approval gates from `detail-flow`
- Preserve the `1:3` master plus `9:21` slice workflow
- Use `IMAGE_BACKEND` plus provider-specific credentials
- Run single-image generation through `detail_flow_use_image_api.py`
- Run slice batches through `detail_flow_use_image_api.py --manifest`

## Configuration

Set `IMAGE_BACKEND` and provider-specific credentials in the current environment or `.env`. See `.env.example` for the full backend matrix.

## Examples

```bash
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "A polished 1:3 product continuity master" --aspect-ratio "1:3" --filename "product_master_1x3.png" --topic-hint "smart fan"
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/smart-fan/images/image_prompts.json"
```

## Source workflow

This skill is based on `detail-flow`, but it is independently runnable and does not import `image-gen-use-api` at runtime.
