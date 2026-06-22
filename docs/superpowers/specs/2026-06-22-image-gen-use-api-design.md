# image-gen-use-api Design

## Summary

`image-gen-use-api` is a new self-contained skill that extracts the API-based image generation capability from `D:\04git\ppt-master\ppt-master-2.9.0` into a reusable skill package.

The skill will support all image generation backends currently supported by `ppt-master`, reuse the same provider-specific `.env` configuration style, default to single-image generation from a prompt, and also support manifest-driven batch generation. Generated assets will be written under the current workspace root in `project/<topic-slug>/images/`, where `<topic-slug>` is inferred automatically from the active conversation context.

## Goals

- Create a reusable skill named `image-gen-use-api`.
- Keep the skill fully self-contained, with no runtime dependency on the local `ppt-master-2.9.0` repository.
- Support all image generation backends defined by `ppt-master` at design time:
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
- Reuse the same configuration model as `ppt-master`:
  - `IMAGE_BACKEND` selects the active provider.
  - Provider-specific environment variables hold credentials, model names, and optional base URLs.
- Default to single-image generation when the user supplies a normal prompt.
- Support batch generation when the user explicitly requests multiple images or provides a manifest.
- Save outputs under `project/<topic-slug>/images/` beneath the current workspace root.
- Automatically derive a topic slug from conversation context without requiring the user to manually provide a project name.

## Non-Goals

- Rebuilding the full `ppt-master` project workflow.
- Supporting non-image tools from `ppt-master`, such as image search, formula rendering, SVG editing, or slide generation.
- Automatically switching to a fallback provider when the configured provider fails.
- Depending on `ppt-master` source files at runtime.
- Preserving backward compatibility with deprecated global image config keys such as `IMAGE_API_KEY`, `IMAGE_MODEL`, or `IMAGE_BASE_URL`.

## User Experience

The skill should expose a simple default behavior:

- If the user provides a prompt such as "generate an image of a futuristic city", the skill generates one image by default.
- If the user explicitly asks for multiple images, or provides a manifest file, the skill switches to batch mode.
- The active backend is determined only by `.env` or current process environment variables. The skill does not ask the user to choose a backend during normal execution.
- The skill automatically creates a project directory under the current workspace root and stores outputs in `project/<topic-slug>/images/`.

The intended result is a low-friction skill for "prompt in, image out" use, while still preserving project-style organization and recoverability.

## Recommended Architecture

The implementation will follow a three-layer structure.

### 1. Skill description layer

Files:

- `skills/image-gen-use-api/SKILL.md`
- `skills/image-gen-use-api/README.md`
- `skills/image-gen-use-api/.env.example`

Responsibilities:

- Describe how the skill should be invoked.
- State that single-image mode is the default.
- Explain when batch mode should be used.
- Document required dependencies and configuration.

### 2. Unified entrypoint

Primary file:

- `skills/image-gen-use-api/image_gen_use_api.py`

Responsibilities:

- Parse input mode: single image or manifest batch.
- Resolve the current workspace root.
- Infer a safe topic slug from conversation context supplied by the host.
- Create the output directory structure.
- Load configuration.
- Resolve the configured backend.
- Normalize work into a shared internal task structure.
- Dispatch generation requests.
- Save results and return a concise execution summary.

### 3. Internal support modules

Files:

- `skills/image-gen-use-api/config.py`
- `skills/image-gen-use-api/project_paths.py`
- `skills/image-gen-use-api/providers/`

Responsibilities:

- `config.py`
  - Resolve `.env` files.
  - Load provider-specific keys.
  - reject deprecated global image keys.
- `project_paths.py`
  - Sanitize and derive topic slugs.
  - Create `project/<topic-slug>/images/`.
  - Handle duplicate session directories and duplicate filenames.
- `providers/`
  - One module per provider.
  - Encapsulate provider-specific HTTP payloads, defaults, and response parsing.

This architecture keeps the user-facing behavior simple while keeping provider complexity isolated behind a stable entrypoint.

## Configuration Design

The new skill should preserve the mental model already used by `ppt-master`.

### Active backend selection

- The active backend is selected by `IMAGE_BACKEND`.
- The skill supports canonical names and selected aliases internally, but user-facing documentation should teach canonical names first.
- The configured backend is the only backend used for a run.

### Supported configuration sources

Configuration resolution order:

1. Current process environment variables
2. `.env` in the current working directory
3. `.env` in the skill directory
4. `.env` in the current workspace root
5. `~/.image-gen-use-api/.env`

Only the first existing `.env` file should be loaded as the fallback layer. Keys are not merged across multiple `.env` files. Current process environment variables always win.

### Deprecated global keys

The following keys are intentionally unsupported:

- `IMAGE_API_KEY`
- `IMAGE_MODEL`
- `IMAGE_BASE_URL`

If any of these keys are present, the skill should fail early with an actionable error telling the user to use `IMAGE_BACKEND` and provider-specific keys instead.

### Provider-specific configuration

Each provider module declares:

- default model name
- required credential environment variables
- optional base URL override variable
- optional provider-specific output parameters

The entrypoint performs shared validation, while provider modules handle provider-specific request shaping.

### Backend coverage

The skill must cover all image generation backends present in `ppt-master` at design time:

- Core: `openai`, `gemini`, `qwen`, `zhipu`, `volcengine`
- Extended or experimental: `minimax`, `stability`, `bfl`, `ideogram`, `siliconflow`, `fal`, `replicate`, `openrouter`, `modelscope`

## Input Model

The skill supports two input modes.

### Single-image mode

Used when the user provides a normal prompt and does not explicitly request multiple images.

Behavior:

- Generate exactly one image by default.
- Internally normalize the request into the same task structure used for batch processing.
- Save the image into the generated project directory.
- Write a minimal manifest alongside the output for traceability.

### Batch mode

Used when:

- the user explicitly requests multiple images, or
- the user provides a manifest file.

Manifest schema should remain close to `ppt-master` while staying minimal.

Top-level fields:

- `items` is required.
- Optional metadata such as `project`, `generated_at`, or style context may be preserved when present.

Required item fields:

- `filename`
- `prompt`
- `aspect_ratio`
- `status`

Optional item fields:

- `image_size`
- `model`
- `purpose`
- `alt_text`
- `last_error`

Status values:

- `Pending`
- `Generated`
- `Failed`
- `Needs-Manual`

Batch reruns should process only `Pending` and `Failed` items.

## Output Directory Design

### Root location

- The root output location is always the current workspace root.
- All generated projects live under `project/`.

### Topic slug derivation

- The skill derives a filesystem-safe topic slug from the active conversation context.
- The slug must be ASCII-safe, concise, and stable enough for human browsing.
- The initial implementation should prefer simple deterministic sanitization over opaque heuristics.

### Directory layout

Primary layout:

- `project/<topic-slug>/images/`

Collision behavior:

- If `project/<topic-slug>/` already exists for a previous session, the skill creates a fresh sibling directory such as:
  - `project/<topic-slug>-2/`
  - `project/<topic-slug>-3/`

This keeps separate conversations from overwriting one another while still grouping related work by theme.

### File naming

- Single-image mode defaults to `image.png`.
- If the backend returns another format, the file extension should match the actual output format.
- If a filename collision occurs inside the same `images/` directory, the skill appends numeric suffixes such as `image_2.png`.
- Batch mode respects manifest `filename` values.

### Sidecar files

The `images/` directory should also contain `image_prompts.json` so results are traceable and rerunnable.

## Internal Task Model

Single-image and batch flows should converge into one shared internal manifest-like structure.

Example shape:

```json
{
  "project": "tech-poster",
  "generated_at": "2026-06-22",
  "items": [
    {
      "filename": "image.png",
      "prompt": "A futuristic blue technology poster",
      "aspect_ratio": "1:1",
      "image_size": "1K",
      "status": "Pending"
    }
  ]
}
```

This avoids maintaining separate execution pipelines for single-image and batch use cases.

## Execution Flow

The execution flow should be fixed and predictable.

1. Parse user intent into single-image or batch mode.
2. Infer a topic slug from conversation context.
3. Create `project/<topic-slug>/images/`, or a numbered sibling when needed.
4. Load configuration from process environment and fallback `.env`.
5. Validate `IMAGE_BACKEND` and provider-specific required variables.
6. Resolve the backend module.
7. Normalize input into the shared task model.
8. Execute image generation.
9. Save image outputs and write or update `image_prompts.json`.
10. Return a summary containing backend, model, output path, and item results.

## Concurrency Strategy

- Single-image mode always runs serially.
- Batch mode may run concurrently.
- Default batch concurrency is `3`.
- `IMAGE_CONCURRENCY` can override the default.
- On rate-limit errors in batch mode, concurrency should be reduced automatically, down to a minimum of `1`.
- Already successful items should never be rerun during the same recovery cycle.

This mirrors the behavior that proved useful in `ppt-master` while keeping the default case simple.

## Error Handling

Error handling should prioritize actionable failures over raw stack traces.

### 1. Configuration errors

Examples:

- missing `IMAGE_BACKEND`
- missing `OPENAI_API_KEY` when `IMAGE_BACKEND=openai`

Behavior:

- Fail before any request is sent.
- Return a precise message identifying the active backend and the missing variable.

### 2. Input validation errors

Examples:

- malformed manifest JSON
- missing `items`
- missing `prompt` for a manifest item
- unsupported `aspect_ratio`

Behavior:

- Fail during validation.
- Use field-level messages such as `items[2].prompt must be a non-empty string`.

### 3. Backend request failures

Examples:

- 401 unauthorized
- 429 rate limit
- provider 5xx error
- network timeout

Behavior:

- Single-image mode fails fast and returns the reason.
- Batch mode marks only the affected item as `Failed` and records `last_error`.

### 4. Recoverable rate-limit handling

Behavior:

- Only batch mode performs automatic rate-limit recovery.
- Rate-limited items are requeued.
- Concurrency is reduced, for example `3 -> 1`, before retrying.

### 5. File system issues

Examples:

- target directory already exists
- output path is not writable
- filename collision

Behavior:

- create numbered session directories when needed
- create numbered filenames when needed
- fail clearly if the workspace is not writable

## Failure Recovery

- Single-image mode should not pretend partial success.
- Batch mode uses the manifest as the recovery checkpoint.
- Re-running batch generation should skip `Generated` items and process only `Pending` and `Failed` items.
- The skill must not silently switch providers on failure.

## Provider Isolation Rules

Each provider module should own:

- request payload construction
- endpoint selection
- provider-specific model defaulting
- response parsing
- output format interpretation

The shared entrypoint should own:

- configuration resolution
- backend selection
- manifest validation
- directory creation
- retry and concurrency policy
- status persistence

This keeps backend-specific complexity from leaking into common logic.

## Testing Strategy

Testing should be organized in four layers.

### 1. Configuration tests

- Reads current process environment first.
- Falls back to `.env` in the defined order.
- Rejects deprecated global keys.
- Produces clear errors when required provider variables are missing.

### 2. Path and directory tests

- Uses current workspace root as the base.
- Creates `project/` automatically when needed.
- Produces safe topic slugs.
- Creates numbered sibling directories for repeated sessions.
- Avoids overwriting existing image files.

### 3. Single-image tests

- A prompt with no explicit multi-image request generates one image.
- A minimal manifest sidecar is created.
- Output summary includes backend, model, and file path.

### 4. Batch tests

- Validates manifest schema.
- Processes only `Pending` and `Failed` items.
- Writes back `Generated`, `Failed`, and `last_error` correctly.
- Reduces concurrency after rate-limit failures.

### 5. Provider smoke coverage

- The registry must include every backend supported by `ppt-master` at design time.
- Each provider must declare required configuration and a default model.
- At least one or two common real backends, preferably `openai` and `gemini`, should be exercised in integration validation when credentials are available.

## Acceptance Criteria

The design is complete when the implementation can satisfy all of the following:

- The new skill is named `image-gen-use-api`.
- The skill is fully self-contained and does not require the local `ppt-master-2.9.0` repository at runtime.
- The skill supports all image generation backends listed in this document.
- The skill accepts a normal prompt and defaults to generating one image.
- The skill accepts a manifest and runs batch generation.
- The skill uses `IMAGE_BACKEND` plus provider-specific configuration variables.
- The skill rejects deprecated global image keys.
- The skill writes output under `project/<topic-slug>/images/` beneath the current workspace root.
- The skill creates new numbered project directories instead of overwriting outputs from prior sessions.
- The skill produces actionable error messages.
- The skill writes or updates `image_prompts.json` so outputs remain traceable.

## Open Design Decisions Resolved In This Spec

The following decisions were explicitly made during brainstorming and are now locked for implementation planning:

- Default mode is single-image generation.
- Batch mode is still supported.
- The topic slug is inferred automatically from context, not supplied by the user by default.
- Backend switching happens only through `.env` or current process environment configuration.
- The output root is the current workspace root.
- The skill is reusable and general-purpose, not tied exclusively to `ppt-master`.
- The skill is fully self-contained.

## Implementation Planning Boundary

This document intentionally stops at design. It defines behavior, structure, constraints, and acceptance criteria, but does not yet prescribe a task-by-task implementation sequence. The next step after user review is to turn this design into an implementation plan via the `writing-plans` skill.
