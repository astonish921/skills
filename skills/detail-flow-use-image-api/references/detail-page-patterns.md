# Detail Page Patterns

This reference describes the workflow patterns for ecommerce detail pages used by `detail-flow-use-image-api`.

## Image generation flow

- For image-generation tasks, write a master long-page prompt first, then execute `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "<prompt>" --aspect-ratio "1:3" --filename "product_master_1x3.png"` for the continuity master when needed.
- For final slices, create `image_prompts.json` in the target `images/` folder and execute `python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/<topic-slug>/images/image_prompts.json"`.
- Use `9:21` for tall slice compositions and keep the `1:3` master aligned with the same prompt family.

## Workflow notes

- The workflow stays blueprint-first and audit-heavy.
- The image step is always an explicit local API call, not a generic instruction to use another skill.
- Keep filenames and prompts stable enough for review and reruns.
