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

It then generates a caption with an **LLM (OpenAI API)** and publishes both images to Instagram through Meta's **official Instagram API with Instagram Login** (`graph.instagram.com`), which fetches the images from S3-compatible object storage. Hashtags are pre-determined and configured in YAML, not generated.

The same functionality is exposed over HTTP by a self-contained **FastAPI** service
(`api/`) with Swagger docs at `/docs`: each stage has its own authenticated
multipart upload endpoint, and `POST /api/v1/posts` runs the full pipeline. Auth is a
single hardcoded login in `config.yaml` (`auth:`) issued as a JWT in an HttpOnly cookie.

Pipeline stages, in order:

```
source photo
  -> Step 1  image_processing   extract EXIF + compose 1:1 bordered image (HTML -> PNG)
  -> Step 2  renderer           render HTML metadata card to PNG (Playwright)
  -> Step 3  caption            generate caption text (OpenAI LLM, vision)
  -> Step 4  uploader           upload photo + metadata card (official API)
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
  uploader/               # Step 4: publish to Instagram
    official.py           #   official API (Instagram Login) container flow + JPEG
    storage.py            #   S3-compatible upload/download (public image hosting)
  api/                    # FastAPI service (self-contained HTTP layer)
    app.py                #   app factory + Swagger metadata
    auth.py               #   JWT/cookie core (token helpers, get_current_user)
    dependencies.py       #   shared DI (pipeline service, upload reader, responses)
    service.py            #   PipelineService: runs stages, framework-agnostic
    models.py             #   strict pydantic request/response schemas
    routes/               #   one route per file, grouped by exposure
      __init__.py         #     aggregates auth + protected + system routers
      auth/               #     public login/logout + authenticated /auth/me
      protected/          #     pipeline stages; auth applied once at router level
      system/             #     public /health
    __main__.py           #   `python -m instagram_pipeline.api` launches uvicorn
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
- **YAML config for secrets**: `config.yaml` holds the OpenAI key, Instagram access token,
  S3 credentials, tags, template name. It is gitignored. `load_config()` validates it
  into typed pydantic models and errors clearly if the file is missing. There are no
  source/output directory settings — only `paths.templates_dir` (the bundled HTML templates).
- **No local file state**: the pipeline is fully in-memory. Source photos arrive as bytes;
  EXIF (`exif.Image(bytes)`), composition, and the metadata card all operate on bytes, and
  Playwright returns the screenshot bytes directly. Generated PNGs are persisted to S3
  (`uploader/storage.py`) in `create_post`, and `GET /posts/{id}/images/{kind}` streams them
  back from S3 (`S3Uploader.download`). Nothing is written to disk, so the chart needs no PVC.
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
- **Instagram upload**: Meta's **Instagram API with Instagram Login**
  (`graph.instagram.com`). The generated PNGs are stored in S3 for downloads, then converted
  to JPEG and re-uploaded to S3-compatible storage (`uploader/storage.py`) and published via
  the container flow (`uploader/official.py`) since Meta fetches media from public URLs.
  Requires a Professional (Business/Creator) account, a long-lived access token, and the
  `s3:` config section. Carousels use `media_type=CAROUSEL`; a single image publishes directly.
- **Docker / Helm**: `Dockerfile` builds the API image (uv + Playwright Chromium). `docker-compose.yml`
  runs the API plus MinIO (S3) and a `minio-init` job that creates the bucket and allows
  anonymous download. The Helm chart has no PVC: generated images live in S3, not on disk.
  In Kubernetes the non-secret `config.yaml` comes from a ConfigMap and
  secret fields are injected as env vars (`load_config` overlays them): `OPENAI_API_KEY`,
  `INSTAGRAM_ACCESS_TOKEN`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `AUTH_PASSWORD`,
  `AUTH_SECRET_KEY`, plus the `S3_*` settings. The public image URL Meta fetches is
  `{S3_ENDPOINT_URL}/{bucket}/{key}`, so `S3_ENDPOINT_URL` must be Meta-reachable.
- **LLM captions**: `openai` SDK, which supports any OpenAI-compatible endpoint
  (OpenRouter, local proxies) via `openai.base_url` in `config.yaml`. The caption is
  generated from the **composed photo image** (base64 vision input), not from metadata —
  the model must support image input. The LLM writes only the caption body; the
  configured hashtags are appended programmatically.
- **API auth**: a single hardcoded login (`auth:` in `config.yaml`) is exchanged at
  `POST /api/v1/auth/login` for a signed JWT that is returned in the body and set as an
  HttpOnly cookie (`SameSite=Lax`, `Secure` configurable). `auth.secret_key` must be a
  long random value and kept stable — changing it invalidates all sessions. The long
  default expiry (`token_expire_minutes`, 30 days) keeps the login persistent. Only
  `/health` and `/auth/login` are public; the `routes/protected/` router applies
  `get_current_user` **once** as a router-level dependency, so stage handlers stay free
  of an unused user parameter. `get_current_user` accepts the cookie or an
  `Authorization: Bearer` token.
- **API stage isolation**: stage endpoints are plain `def` (not `async def`) because
  Playwright's sync API cannot run inside FastAPI's asyncio event loop; FastAPI runs them
  in a worker thread. `PipelineService` is framework-agnostic and each stage method
  (`compose`, `render`, `caption`) is reused by `create_post`.

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
uv run python -m instagram_pipeline.api                               # FastAPI + Swagger at /docs
docker compose up --build                 # API + MinIO (S3 image hosting)
uv run ruff check .                       # lint
uv run mypy src                           # strict typecheck
```

Run `ruff check`, `mypy src`, and `pytest` after every change. All three must pass.

## Manual `if __name__ == "__main__"` testing

Image and caption component modules have a `if __name__ == "__main__":` block that runs the
step in isolation and prints a short result. Use them to see what each stage does without
running the whole pipeline. `caption/generator.py` needs a real OpenAI key. The uploader is
only reached through the pipeline / FastAPI service; it talks to the official Instagram API
and S3 and has no standalone entry point.

## Testing Conventions

- One `tests/test_<component>.py` per package. External services (OpenAI, Instagram)
  are **faked/stubbed**, never called; network-free and directory-scoped via `tmp_path`.
- `test_photo_metadata.py` writes EXIF/GPS fixtures with the `exif` package itself.
- Renderer tests call real Playwright (Chromium is installed for the project) but pass no
  `lat`/`lng`, so the map (and its network tiles) is skipped and tests stay offline.
- `test_api.py` uses FastAPI's `TestClient` and overrides `get_pipeline_service` (and
  `get_current_user`) via `app.dependency_overrides`, so no real config, Playwright,
  LLM, or Instagram calls happen. Auth tests override `get_auth_settings` with a fake
  `AuthSettings` and exercise the real login/cookie/`/auth/me` flow.
- Manual verification checklist: the composed photo is exactly the configured size
  (default 1080x1080), the metadata card is exactly the viewport size, and non-blank
  (renders the template, including the map when GPS is present), captions are generated
  from the composed photo image (vision) and append configured hashtags, the generated PNGs
  are stored in S3 and stream back from `GET /posts/{id}/images/{kind}`, and the uploader
  converts both PNGs to JPEG, uploads them to S3, and publishes a carousel (or single image).

## Guardrails

- `config.yaml` is gitignored. Never commit secrets.
- Keep output exactly 1:1 at every image step — Instagram feeds render squares.
- Do not reintroduce local output files: generated images belong in S3 (and only transiently
  in `/tmp` for Playwright). The chart intentionally ships no PVC.
- The official API does not accept byte uploads: images must be reachable at a public URL
  (the `s3:` section) for the duration of the publish. Be careful not to leave objects public
  longer than needed.
- When exposing the API publicly: set a long random `auth.secret_key`, change the default
  `auth.password`, and set `auth.cookie_secure: true` behind HTTPS. Only `/health` and
  `/auth/login` may stay public — never drop `get_current_user` from a stage endpoint.
- Playwright is a test-time dependency of runtime rendering, not just a dev tool: after
  changing the renderer, re-run `uv run playwright install chromium` if the browser cache
  is missing.
