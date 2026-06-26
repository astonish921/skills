---
name: detail-flow-use-image-api
description: Build, plan, audit, and deliver product detail pages and long ecommerce image sets while using explicit API-backed image generation through the local `detail_flow_use_image_api.py` entrypoint.
---

# detail-flow-use-image-api

Use this skill when the user wants the `detail-flow` workflow, but image generation must be executed locally through the API-backed `detail_flow_use_image_api.py` script instead of delegating to another image skill at runtime.

This variant keeps the blueprint-first, audit-heavy ecommerce page workflow and the two normal user approval gates. Every image-generation step must be made explicit as a local command that uses `IMAGE_BACKEND` and provider-specific credentials from the environment or `.env`.

## Behavior

- keep the `detail-flow` structure: blueprint, continuity master, first two slices, preview, remaining slices, and final audit
- use `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py` for single-image masters and targeted reruns
- use `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest <path>` for multi-slice batches
- write outputs and manifests under `project/<topic-slug>/images/` unless the workflow intentionally supplies `--output-dir`
- prefer `IMAGE_BACKEND` plus provider-specific keys such as `OPENAI_API_KEY` or `GEMINI_API_KEY`
- when `IMAGE_BACKEND=gemini`, pass `--reference-image <product-image-path>` when product-detail consistency matters
- do not switch to `image-gen-use-api` at runtime

## Execution contract

- when the workflow asks for a `1:3` master, call `detail_flow_use_image_api.py` explicitly in single-image mode
- when the workflow asks for the first two slices or remaining slices, call `detail_flow_use_image_api.py --manifest <path>` or use a single-image repair run when only one slice needs correction
- keep the prompt and filename explicit in the command line so the generated asset can be audited later
- when using Gemini for product-led generation, include `--reference-image` or a manifest `reference_image` field so the product image is sent as multimodal input instead of only being described in text

## Examples

```bash
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "A polished 1:3 product continuity master" --aspect-ratio "1:3" --filename "product_master_1x3.png" --topic-hint "smart fan" --reference-image "D:/assets/product.png"
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/smart-fan/images/image_prompts.json"
```

## Configuration notes

- Set `IMAGE_BACKEND` in the current environment or in `.env`.
- Use provider-specific credentials and model keys.
- Keep the skill self-contained and document the image API workflow directly in this skill.
