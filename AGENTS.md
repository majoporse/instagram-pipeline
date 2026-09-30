# AGENTS.md — instagram-pipeline

Instructions for AI coding agents working in this repository.

## Project Overview

An Instagram posting pipeline. For each source photo it produces **two** exact 1:1 images:

1. **Composed photo** — the source photo placed **centered** on a solid background with a
   **minimum border**. Rendered from an HTML template (`renderer/templates/composed.html`)
   so the layout is CSS: `object-fit: contain` scales the photo to fill the border box
   without cropping or stretching, preserving aspect ratio.
2. **Metadata card** — an HTML template (`renderer/templates/metadata.html`) rendered to PNG
   showing the photo's EXIF details (camera, ISO, shutter, aperture, location, date)
   directly on a light-gray background with hairline underlines, plus a small OpenStreetMap
   map when the photo carries GPS coordinates.

It then generates a caption with an **LLM (OpenAI API)** and uploads both images to Instagram using **instagrapi**. Hashtags are pre-determined and configured in YAML, not generated.

Pipeline stages, in order:

```
source photo
  -> Step 1  image_processing   extract EXIF + compose 1:1 bordered image (HTML -> PNG)
  -> Step 2  renderer           render HTML metadata card to PNG (Playwright)
  -> Step 3  caption            generate caption text (OpenAI LLM, vision)
  -> Step 4  uploader           upload photo + metadata card (instagrapi)
```

## Repository Layout (mirrors the pipeline)

```
src/instagram_pipeline/
  config.py               # strict config loading (pydantic + PyYAML)
  pipeline.py             # orchestrator wiring the steps together
  image_processing/       # Step 1: EXIF extraction + bordered 1:1 composition
    photo_metadata.py     #   EXIF reader (GPS, camera, exposure)
    bordered_image.py     #   compose 1:1 bordered image (HTML template -> PNG)
  renderer/               # Step 2: Jinja2/HTML -> PNG
    renderer.py
    templates/            #   HTML/Jinja2 templates (composed.html, metadata.html)
  caption/                # Step 3: LLM caption generation
    generator.py
  uploader/               # Step 4: instagrapi upload with session persistence
    publisher.py
input/photos/             # source images (gitignored)
output/                   # generated images + instagrapi session (gitignored)
config.yaml               # SECRETS — copy from config.yaml.example, never commit
config.yaml.example       # committed template documenting every setting
tests/                    # pytest suite, one file per component
main.py                   # CLI entrypoint
```

Keep this structure. New pipeline features go inside the matching `src/instagram_pipeline/*` package.

## Key Technical Decisions

- **UV project** (`uv` 0.11+, Python 3.13, `src/` layout with hatchling). Never add deps
  or create an environment with `pip`/`venv` directly.
- **Strict typing everywhere**: `mypy --strict` passes, pydantic v2 models for all
  config/data, dataclasses for stateless service objects, `from __future__ import
  annotations`. Do not loosen these settings without a strong reason.
- **YAML config for secrets**: `config.yaml` holds OpenAI key, Instagram credentials,
  paths, tags, template name. It is gitignored. `load_config()` validates it into typed
  pydantic models and errors clearly if the file is missing.
- **HTML rendering**: Playwright (headless Chromium) renders Jinja2 templates at an
  exact viewport, screenshotted at viewport size (not `full_page`) so output is always
  exactly 1080x1080. Bordered composition uses `object-fit: contain` — scale to fit,
  never crop or stretch.
- **EXIF / GPS**: `image_processing/photo_metadata.py` reads EXIF with the `exif` package
  (`make`/`model`, `photographic_sensitivity`, `exposure_time`, `f_number`,
  `datetime_original`, GPS) and returns a typed `PhotoMetadata`. `PhotoMetadata.context()`
  produces the metadata-card context; GPS adds `lat`/`lng`.
- **Map**: the metadata card embeds a Leaflet map driven by `render.map_tiles` in
  `config.yaml` (default: keyless CARTO Positron, light — alternatives: Voyager, Dark
  Matter, OpenStreetMap). It is shown only when `lat`/`lng` are present; zoom/attribution
  controls are disabled for a clean render. This needs network at render time; tests
  render without GPS so they stay offline.
- **Instagram upload**: `instagrapi` (private API). Session is persisted to
  `output/sessions/session.json` and reloaded — never accept account logins on every run.
- **LLM captions**: `openai` SDK, which supports any OpenAI-compatible endpoint
  (OpenRouter, local proxies) via `openai.base_url` in `config.yaml`. The caption is
  generated from the **composed photo image** (base64 vision input), not from metadata —
  the model must support image input. The LLM writes only the caption body; the
  configured hashtags are appended programmatically.

## Commands (always via uv)

```bash
uv sync                                   # install everything (dev group included)
uv add <package>                          # add a runtime dep
uv add --dev <package>                    # add a dev dep (lint/typing/tests)
uv run pytest                             # run the suite
uv run python -m instagram_pipeline.image_processing.photo_metadata     # prints EXIF for a photo
uv run python -m instagram_pipeline.image_processing.bordered_image   # manual test a step
uv run python -m instagram_pipeline.renderer.renderer                 # renders metadata_card.png
uv run python -m instagram_pipeline.caption.generator                 # needs real OPENAI key
uv run python -m instagram_pipeline.uploader.publisher                # posts for real + needs creds
uv run ruff check .                       # lint
uv run mypy src                           # strict typecheck
```

Run `ruff check`, `mypy src`, and `pytest` after every change. All three must pass.

## Manual `if __name__ == "__main__"` testing

Every component module has a `if __name__ == "__main__":` block that runs the step in
isolation and prints a short result. Use them to see what each stage does without running
the whole pipeline. Steps touching external services (caption, uploader) require real
credentials in `config.yaml` and are intentionally not automated in tests.

## Testing Conventions

- One `tests/test_<component>.py` per package. External services (OpenAI, Instagram)
  are **faked/stubbed**, never called; network-free and directory-scoped via `tmp_path`.
- `test_photo_metadata.py` writes EXIF/GPS fixtures with the `exif` package itself.
- Renderer tests call real Playwright (Chromium is installed for the project) but pass no
  `lat`/`lng`, so the map (and its network tiles) is skipped and tests stay offline.
- Manual verification checklist: the composed photo is exactly the configured size
  (default 1080x1080), the metadata card is exactly the viewport size, and non-blank
  (renders the template, including the map when GPS is present), captions are generated
  from the composed photo image (vision) and append configured hashtags, uploader passes
  the right path/caption to `photo_upload`.

## Guardrails

- `config.yaml`, `output/`, `input/photos/*`, and `*.session.json` are gitignored. Never
  commit secrets or sessions.
- Keep output exactly 1:1 at every image step — Instagram feeds render squares.
- Don't loop-retry Instagram after `feedback_required`/`challenge_required`; back off.
- Playwright is a test-time dependency of runtime rendering, not just a dev tool: after
  changing the renderer, re-run `uv run playwright install chromium` if the browser cache
  is missing.
