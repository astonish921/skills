# detail-flow-use-image-api Design

## Summary

`detail-flow-use-image-api` is a new self-contained skill that forks the proven `detail-flow` long-page workflow and replaces every image-generation step with explicit API-backed generation instructions.

The new skill is intended to preserve the strongest part of `detail-flow`: the blueprint-first, review-gated, audit-heavy workflow for product detail pages and long ecommerce image sets. The new skill must remain independently usable, so it may copy implementation patterns from `skills/image-gen-use-api/`, but it must not depend on that skill at runtime.

## Goals

- Create a new standalone skill named `detail-flow-use-image-api`.
- Preserve the core `detail-flow` workflow, especially:
  - analyze inputs first
  - produce the full page blueprint before generation
  - stop for user approval at the blueprint gate
  - establish text and visual masters before final slice generation
  - generate the first two slices and preview before the second approval gate
  - audit generated outputs before continuing
  - preserve approved outputs and revise at the smallest responsible layer
- Replace all generic image-generation language in `detail-flow` with explicit API-calling behavior.
- Reuse the same backend-selection model already established by `image-gen-use-api`:
  - `IMAGE_BACKEND` selects the active provider
  - provider-specific credentials and optional model settings come from environment variables
- Keep the new skill fully self-contained with no runtime dependency on `skills/image-gen-use-api/`.
- Support both single-image generation and manifest-driven multi-image generation inside the new skill so the workflow can handle masters and slice batches consistently.

## Non-Goals

- Redesigning the `detail-flow` workflow from scratch.
- Turning the new skill into a generic image-generation utility divorced from long-scroll detail-page work.
- Introducing a new backend configuration scheme.
- Automatically switching to a fallback backend when the configured provider fails.
- Replacing the review and approval gates from `detail-flow` with a fully automated pipeline.
- Refactoring unrelated parts of the existing skills repository.

## Context and Constraints

The repository already contains two relevant assets:

- `skills/detail-flow/SKILL.md`, which has a mature workflow for product detail pages and long ecommerce image sets.
- `skills/image-gen-use-api/SKILL.md`, which defines the current API-backed image-generation behavior and backend configuration model.

The user explicitly requested a minimal-replacement design:

- keep `detail-flow` as intact as possible
- keep `IMAGE_BACKEND` as the backend policy
- make the new skill independent rather than wrapping or invoking `image-gen-use-api` at runtime

This means the safest design is a direct fork of `detail-flow` with carefully targeted substitutions around image generation.

## User Experience

The user experience should feel like `detail-flow`, not like a standalone image CLI.

When the skill is invoked for a product-detail or long ecommerce page task:

1. The skill analyzes product inputs, reference style, known facts, and unknowns.
2. The skill produces the full 8-screen blueprint before image generation begins.
3. The user approves or revises the blueprint.
4. The skill prepares the text master, visual master description, and structure blueprint.
5. Wherever the original workflow would say to generate a master or slice, the new skill explicitly calls its own API-backed generation script.
6. The skill inspects the `1:3` master, the first two slices, and a concatenated preview before presenting them for approval.
7. After the second approval gate, the skill generates the remaining slices, performs the final audit, and delivers the folder path.

The new behavior should be explicit and reproducible. The agent should not rely on vague phrasing such as "generate images" when the skill actually requires a script call with a prompt or manifest.

## Recommended Architecture

The implementation should use a compact two-part skill package.

### 1. Skill definition layer

Primary file:

- `skills/detail-flow-use-image-api/SKILL.md`

Responsibilities:

- describe the workflow in the same overall shape as `detail-flow`
- preserve the approval gates and audit rules
- define exactly where explicit API generation must happen
- describe how single-image and manifest batch generation are used in different stages of the workflow
- document backend configuration, dependencies, and output behavior

### 2. Self-contained generation entrypoint

Primary file:

- `skills/detail-flow-use-image-api/detail_flow_use_image_api.py`

Responsibilities:

- load configuration from process environment and fallback `.env`
- validate `IMAGE_BACKEND` and provider-specific required keys
- accept direct prompt input for single-image generation
- accept a manifest for batch generation
- create deterministic output directories
- dispatch requests to the configured provider
- save outputs and execution metadata
- return concise success and failure summaries that the calling workflow can audit

This architecture keeps the workflow centered in `SKILL.md` while making the script responsible only for explicit API-backed image generation.

## File Layout

The initial implementation should stay intentionally small.

Required files:

- `skills/detail-flow-use-image-api/SKILL.md`
- `skills/detail-flow-use-image-api/detail_flow_use_image_api.py`

Optional files only if needed to keep the entrypoint readable:

- `skills/detail-flow-use-image-api/README.md`
- `skills/detail-flow-use-image-api/.env.example`
- `skills/detail-flow-use-image-api/providers/`

The default preference is to avoid creating a large module tree unless the copied provider logic becomes too hard to maintain in one file. The design favors minimal surface area over architectural purity.

## Workflow Mapping

The new skill should preserve the structure of `detail-flow` and map generation stages to explicit script calls.

### Stage 1. Analyze inputs

No API call happens here.

The skill should keep `detail-flow` behavior:

- describe product facts and inferred selling points separately
- identify unknowns that must not be fabricated as confirmed facts
- give the user one concise chance to add confirmed specs or prohibited claims

### Stage 2. Produce the page blueprint first

No API call happens here.

The skill should keep the existing blueprint fields and narrative controls from `detail-flow`, including:

- `slice_id`
- `buyer_question`
- `module_type`
- `module_label`
- `claim_seed`
- `screen_job`
- `evidence_type`
- `content_density`
- `layout_archetype`
- `copy_module_type`
- `copy_structure_pattern`
- `primary_module`
- `secondary_modules`
- `text_exact`
- `hierarchy_strategy`
- `composition_shift`
- `top_edge_anchor`
- `bottom_edge_anchor`
- `visual_composition`
- `reference_style_notes`
- `risk_unknowns`

The user approval gate remains mandatory before any image generation.

### Stage 3. Lock the long-scroll masters and structure

This stage introduces the first explicit API call.

Behavior:

- prepare the text master and visual master description exactly as `detail-flow` requires
- use the approved structure blueprint as the highest-priority input for prompt construction
- explicitly call `detail_flow_use_image_api.py` to generate the `1:3` master when the workflow uses one

The skill text should clearly state that this is not a conceptual "generate image" step. It is an execution step backed by the local script.

### Stage 4. Generate final page sections

This stage uses explicit API calls for slice generation.

Behavior:

- first generate the initial two `9:21` slices using the local script
- use direct prompt mode for isolated single-image runs when that is simpler
- use manifest mode when generating multiple slices in one batch is cleaner or necessary
- concatenate and audit the first two slices before presenting the second approval package
- after approval, generate the remaining slices with the same explicit script-backed approach

The skill should preserve the original continuity requirements from `detail-flow`: slices must read like neighboring sections of one long page rather than standalone posters.

### Stage 5. Prepare split delivery or long-image concat

Generation is complete by this point, but the skill still preserves `detail-flow` delivery behavior:

- keep all approved slice files
- produce concatenated previews and the final long image when required
- verify every expected output exists before reporting completion

### Stage 6. Audit the result

The audit logic stays close to `detail-flow`.

The new skill should still inspect for:

- product drift
- garbled text
- unsupported claims
- poster-like resets between slices
- broken top or bottom continuity
- repeated visual grammar across multiple screens

The difference is that corrective action now explicitly points back to prompt revision, manifest revision, master revision, or regeneration through the local API script.

## Image Generation Design

The new skill should embed the image-generation behavior it needs rather than importing another skill.

### Backend policy

- `IMAGE_BACKEND` is required.
- The configured backend is the only backend used for a run.
- The new skill should support the same backend family documented in `image-gen-use-api`, unless implementation review later finds that a subset must be delayed for a clear technical reason.

Design-time target list:

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

### Configuration loading

Configuration resolution should follow the same principle already used by `image-gen-use-api`:

1. current process environment variables
2. fallback `.env` data

The exact fallback search order can match the current implementation pattern from `image-gen-use-api`, but the new skill should document that environment variables always win.

The skill should not introduce deprecated generic keys such as:

- `IMAGE_API_KEY`
- `IMAGE_MODEL`
- `IMAGE_BASE_URL`

The mental model should remain provider-specific.

### Input modes

The generation script should support two modes.

#### Single-image mode

Used for:

- `1:3` master generation
- one-off slice regeneration
- small targeted repairs where a manifest is unnecessary

Expected input:

- prompt
- optional filename
- optional aspect ratio
- optional model override

#### Manifest batch mode

Used for:

- first two slices when the workflow prefers a bundled run
- remaining slice generation after approval
- any rerun involving multiple slices

The manifest should be close to the current `image-gen-use-api` structure so results remain inspectable and rerunnable.

Required item fields:

- `filename`
- `prompt`
- `aspect_ratio`
- `status`

Optional fields may include:

- `image_size`
- `model`
- `purpose`
- `alt_text`
- `last_error`

## Output Directory Design

The new skill should use deterministic, review-friendly outputs.

### Generation outputs

Image-generation runs should write into a stable image folder such as:

- `project/<topic-slug>/images/`

This keeps the new skill aligned with the existing `image-gen-use-api` behavior and avoids inventing a second unrelated storage model.

### Final delivery outputs

The workflow should still produce the deliverables expected by `detail-flow`, whether the final destination is the same directory tree or a sibling delivery folder.

Expected outputs may include:

- approved `1:3` master
- `screen_01` through `screen_08` final slices
- first-two-slice preview concat
- full long-image concat
- `image_prompts.json` or equivalent run manifest

The design allows the implementation to decide whether intermediate generation assets and final delivery assets live in the same folder or in a closely related delivery folder, as long as the structure is explicit and reproducible.

## Revision Routing

One of the most valuable parts of `detail-flow` is its smallest-responsible-layer revision logic. The new skill should preserve that behavior and tie it directly to API-backed regeneration.

Expected routing:

- wording or copy failure: revise `text_exact`, then regenerate only the affected image region or slice
- product identity failure: strengthen product constraints, then regenerate only the affected slice
- single-screen hierarchy failure: revise that screen's structural fields and regenerate that slice
- adjacent continuity failure: revise edge anchors and regenerate the smallest affected slice span
- repeated multi-screen composition failure: revise `composition_shift` for the affected range and rerun only that range
- whole-page continuity failure: revise the visual master or prompt system, then regenerate only the affected slices when possible
- whole-page narrative failure: return to the blueprint and require renewed approval before broad regeneration

The skill must not default to full regeneration unless the approved story or master has materially changed.

## Error Handling

The skill should fail clearly and early when required capabilities are missing.

### Configuration failures

Examples:

- missing `IMAGE_BACKEND`
- missing provider credential for the selected backend

Behavior:

- stop before sending any request
- state exactly which variable is missing
- do not substitute another provider automatically

### API request failures

Examples:

- authentication failure
- rate limit
- timeout
- provider 5xx response

Behavior:

- fail the current generation step clearly
- preserve already approved assets
- report whether the failure affects a single image or an entire batch
- record enough detail in manifest state or logs for rerun

### Output quality failures

Examples:

- textless master despite planned copy
- garbled visible text
- unrelated poster-like slices
- product drift
- unsupported claims invented by the model

Behavior:

- treat these as audit failures, not successful generation
- route correction to the smallest responsible layer
- do not silently continue to later workflow stages

### Unsupported capability failures

If a required generation or editing capability is unavailable for the configured backend, the skill should state the limitation and stop at the current stage or offer the smallest relevant alternative. It must not fabricate outputs with placeholder assets.

## Independence Requirements

The new skill must be independently usable.

That means:

- loading `detail-flow-use-image-api` alone should be enough for an agent to understand the workflow
- running the script should not require importing code from `skills/image-gen-use-api/`
- copied code is acceptable; runtime coupling is not
- the skill documentation should not tell the agent to switch to `image-gen-use-api` to finish generation

This preserves portability and avoids hidden cross-skill dependencies.

## Testing and Validation Strategy

The implementation plan should validate both workflow correctness and script behavior.

### Documentation validation

- verify that the new `SKILL.md` still preserves the original `detail-flow` approval gates and audit expectations
- verify that every generation stage now references explicit API-backed execution
- verify that the new skill does not accidentally instruct the agent to use the old skill at runtime

### Script validation

- validate argument parsing for single-image mode
- validate manifest parsing for batch mode
- validate configuration loading precedence
- validate backend selection through `IMAGE_BACKEND`
- validate error messages for missing credentials or malformed manifests

### Workflow validation

- check that the documented workflow still reaches the same milestones as `detail-flow`
- check that master generation, first-two-slice generation, and full-slice generation each have explicit execution instructions
- check that revision guidance still routes to the smallest responsible layer

## Risks and Mitigations

### Risk 1. The fork drifts too far from `detail-flow`

Mitigation:

- keep the new `SKILL.md` as a targeted fork rather than a rewrite
- preserve section order and workflow language where possible

### Risk 2. The new skill becomes a thin wrapper around `image-gen-use-api`

Mitigation:

- copy the needed implementation into the new directory
- avoid runtime imports or documentation dependencies on the old skill

### Risk 3. Provider support becomes too large for a minimal fork

Mitigation:

- preserve the existing provider model conceptually
- during implementation, keep provider logic minimal and only split files if readability demands it

### Risk 4. The workflow loses audit discipline because generation is easier to trigger

Mitigation:

- keep the two approval gates explicit
- keep audit steps mandatory before proceeding to later stages
- require failures to stop the workflow rather than glossing over them

## Recommended Implementation Sequence

1. Create `skills/detail-flow-use-image-api/`.
2. Fork `skills/detail-flow/SKILL.md` into the new directory.
3. Replace generic generation instructions with explicit local API script execution guidance.
4. Copy the required script logic from `skills/image-gen-use-api/` into `detail_flow_use_image_api.py`.
5. Adapt the script interface so it can support both master generation and slice batch generation.
6. Verify that the new `SKILL.md` remains self-contained and does not require loading another skill.
7. Validate configuration and output-path behavior.

## Acceptance Criteria

- A new skill named `detail-flow-use-image-api` exists as a separate directory.
- The new `SKILL.md` clearly reads as a `detail-flow`-style workflow rather than a generic image tool.
- The two standard user approval gates from `detail-flow` remain intact.
- Every image-generation stage now uses explicit API-backed execution language.
- `IMAGE_BACKEND` remains the backend-selection mechanism.
- The new skill has no runtime dependency on `skills/image-gen-use-api/`.
- The generation script supports both direct prompt generation and manifest-driven batch generation.
- Output paths and manifests are deterministic enough for review and rerun.
- Failure handling preserves approved outputs and routes fixes to the smallest responsible layer.

## Open Decisions Resolved In This Design

The brainstorming process resolved the main design questions as follows:

- Scope: minimal replacement rather than broad redesign
- Backend policy: continue using `IMAGE_BACKEND`
- Structure: independent fork rather than wrapper dependency
- Recommendation: fork `detail-flow` and replace image-generation stages with explicit API calls

Those decisions remove the main ambiguities and keep the implementation tightly scoped.
