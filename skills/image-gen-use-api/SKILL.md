---
name: image-gen-use-api
description: "Generate images through configured API backends with a confirmation-first SOP: confirm size and style, draft a final prompt for approval, then generate; on edits, either modify from the previous image or re-pick style before regenerating. Single-image mode is the default; batch mode uses a manifest. Outputs are written under project/<topic-slug>/images/."
---

# image-gen-use-api

Use this skill when the user wants image generation, or wants to modify/refine a previously generated image, through one of the configured API backends in `skills/image-gen-use-api/`.

This skill exposes **one primary tool**: `generate_image` (one image per call). Multi-step workflows (confirming size and style, drafting a final prompt for approval, understanding a previous image, and iterating after edits) are driven by **you, the orchestrating model**, following the recipe in `Iterative refinement workflow` below. Do not hardcode this workflow into any dialog layer — you execute it by calling the tool and reasoning across turns.

## Behavior

- single-image mode is the default
- switch to batch mode only when the user explicitly asks for multiple images or provides a manifest path
- choose the provider from `IMAGE_BACKEND`
- load provider settings from the current environment first, then fill missing values from `.env`
- write single-image outputs under `project/<topic-slug>/images/`
- write the run manifest as `project/<topic-slug>/images/image_prompts.json`
- each generate call creates a new `project/<topic-slug>/` folder; the latest image is always at the most recently returned `output_path`

## Primitives

### Generate one image

Call the `generate_image` tool with a complete prompt:

```json
{ "prompt": "<full prompt text>" }
```

The tool runs `python skills/image-gen-use-api/image_gen_use_api.py "<prompt>"` and returns, as the tool result you can read in the conversation:

- `已生成图片：<output_path>` — the generated image is at `output_path` on disk, and is also fed back to you as an image you can view (multimodal)
- the exact prompt you used stays in the conversation as your tool call, so you can recall it next turn

There is **no guaranteed separate** `describe-image` or reference-image tool today:
- to understand a previous image, **view it directly** (it is returned to you as image content after each `generate_image` call, and the previous image is re-attached on refine turns)
- if the current runtime/provider exposes reference-image input, **prefer passing the previous image as a reference** when the user wants to modify on top of the original image
- if no reference-image input is available, fall back to textual understanding of the previous image + the previous prompt

## Response format for this skill

When you need the user to choose from predefined options, reply with:

1. Human-readable Markdown text only — no interactive UI controls, no fenced `ui` blocks

Rules:

- Present options as a plain numbered list or bullet list in Markdown. Ask the user to reply with their choice in normal chat text.
- If the user only needs to confirm a ready prompt, present the prompt and ask them to reply `同意` or describe their own adjustments.
- For edit/refine flows, ask the user to provide all desired changes in a single reply instead of asking across multiple turns.
- For final confirmation flows, prefer a template such as `确认提示词如下：{finalPrompt}` so the backend can continue directly.
- If the user sends `确认提示词如下：...` or `确认提示词，按此生成：...`, treat everything after the colon as an already confirmed final prompt and continue directly to generation without asking for one more confirmation.

### Example: first-generation size and style confirmation

```md
可以，先确认两个关键信息我再帮你整理最终生成提示词。

**1. 画面尺寸/比例（请回复序号或直接说明）：**
1. 1:1 方图
2. 4:3 横版
3. 16:9 横版
4. 9:16 竖版
5. 自定义尺寸（请直接说明）

**2. 画风（请回复序号或直接说明）：**
1. 童话绘本风
2. 电影海报风
3. 国风插画风
4. 暗黑史诗风
5. 自定义（请直接说明）
```

### Example: final prompt confirmation

```md
最终提示词已经整理好，请确认是否继续生成；如果你还想调整，也可以直接说明。

**最终提示词：**
{finalPrompt}

请回复：**同意** 直接生成，或说明你想要的调整。
```

### Example: edit mode choice

```md
继续修改可以一次填完，我会直接按你确认后的提示词继续生成。

请选择修改方式：
1. **尽可能在原来基础上修改** — 请同时说明修改内容，例如：请尽可能在原图基础上修改，保持整体风格不变，只把兔子改得更有冲刺感、更接近终点
2. **重新选择风格** — 可从以下风格中选择：童话绘本风 / 电影海报风 / 国风插画风 / 暗黑史诗风 / 自定义，并同时说明修改内容
```

## Iterative refinement workflow

Follow this recipe whenever the user asks to generate, then modify, an image. The goal is a self-contained SOP that keeps the dialog layer generic while ensuring the user confirms key decisions before generation.

### Default style options

Unless the user already clearly specified a style, offer these defaults first:

- `童话绘本风`
- `电影海报风`
- `国风插画风`
- `暗黑史诗风`
- `自定义`

If the user replies with a free-text style, treat it as `自定义`.

### Phase A — first generation

Run these steps in order:

1. **Read the user's requested image content.** Extract the subject, action, scene, mood, and any constraints they already gave.

2. **Confirm the image size/aspect ratio.** Ask the user for the target size if they did not already specify it. You may phrase this as aspect ratio or output size. Do not proceed until size is clear. Present options as a Markdown numbered list.

3. **Confirm the style.** Offer the default style options above unless the user already specified one clearly enough to skip this step. Present options as a Markdown numbered list. If the user chooses `自定义`, ask them to type the custom style in normal chat text.

4. **Draft the final prompt.** Rewrite the user's request into a single clean production-ready prompt that combines:
   - the requested content
   - the confirmed size/aspect
   - the confirmed style
   - composition, lighting, mood, and detail level as needed

5. **Ask the user to confirm the final prompt.** Show the final prompt before generation. Do not call `generate_image` until the user explicitly confirms that the prompt is OK. Present the prompt and ask the user to reply `同意` or describe their desired adjustments.

6. **Generate.** Call `generate_image` with the confirmed final prompt.

7. **Report the result.** Tell the user the result and keep the final prompt you used in context for future edits.

### Phase B — user requests a modification to the last image

When the user wants to change the previously generated image, first ask them to pick exactly one modification mode. Present options as a Markdown numbered list:

- `1` 尽可能在原来基础上修改
- `2` 重新选择风格

Do not call `generate_image` until they choose one.

#### Mode 1 — modify on top of the previous image

Run these steps in order:

1. **Understand the previous image.** View the previous image (it is attached to the conversation) and extract a concise factual description: subject, palette, composition, style markers, and the parts most relevant to the requested edit.

2. **Recall the previous prompt.** Read it from your last `generate_image` tool call.

3. **Draft a new prompt that stays close to the original.** Combine:
   - the previous prompt
   - the previous image understanding
   - the user's requested change
   Keep the new prompt as close as possible to the original image while applying the requested modification.

4. **If reference-image input is supported, prefer it.** When the current runtime/provider supports passing a reference image, use the previous image as the reference input because it keeps the modification grounded in the original result. If not supported, rely on the textual prompt only.

5. **Ask the user to confirm the new final prompt.** Show the rewritten prompt before regeneration. Ask the user to reply `同意` or describe their desired adjustments.

6. **Regenerate.** After user confirmation, call `generate_image` with the new prompt. If the runtime/provider supports reference-image input, pass the previous image reference as well.

7. **Report the result.** Keep the newest prompt in context for the next round.

#### Mode 2 — re-pick the style

Run these steps in order:

1. **Confirm the new style.** Offer the default style options again:
   - `童话绘本风`
   - `电影海报风`
   - `国风插画风`
   - `暗黑史诗风`
   - `自定义`

2. **Understand the previous image and recall the previous prompt.** Use them as context so you preserve the core scene unless the user asked to change it.

3. **Draft a new final prompt.** Combine:
   - the original scene/content that should be preserved
   - the user's requested modifications
   - the newly selected style
   - any updated size/aspect if the user changed it

4. **Ask the user to confirm the new final prompt.** Do not generate yet. Ask the user to reply `同意` or describe their desired adjustments.

5. **Regenerate.** After confirmation, call `generate_image` with the new prompt.

6. **Report the result.** Keep the newest prompt in context for the next round.

### General rules

- Never skip the final-prompt confirmation step before generation.
- Never skip the size confirmation step on first generation unless the user already made it explicit.
- On edits, prefer preserving the original result when the user chose mode `1`.
- On edits, treat mode `2` as a style reset while preserving the scene unless the user explicitly asked to change the scene itself.

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

Single image:

```bash
python skills/image-gen-use-api/image_gen_use_api.py "A minimal tech poster" --topic-hint "Tech Poster"
```

Batch manifest:

```bash
python skills/image-gen-use-api/image_gen_use_api.py --manifest "project/demo/images/image_prompts.json"
```

## Configuration notes

- Use provider-specific keys such as `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY`.
- Do not use deprecated global keys such as `IMAGE_API_KEY`, `IMAGE_MODEL`, or `IMAGE_BASE_URL`.
