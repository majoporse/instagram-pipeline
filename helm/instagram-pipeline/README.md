# instagram-pipeline

Deploys the pipeline API (FastAPI + Playwright). Minimal: a Deployment, a
Service, a **ConfigMap** with the non-secret `config.yaml`, a **Secret** whose
values are injected as env vars, and optionally an Ingress, a PVC, and a
registry pull Secret.

The app reads the ConfigMap's `config.yaml` and overlays secret fields from the
environment (`OPENAI_API_KEY`, `INSTAGRAM_ACCESS_TOKEN`, `S3_ACCESS_KEY`,
`S3_SECRET_KEY`, `AUTH_PASSWORD`, `AUTH_SECRET_KEY`).

## Prerequisites

- `kubectl` on the cluster, `helm` v3.
- `docker login registry.hatal.cc` and a Harbor project for the image.
- The image built/pushed:

```bash
docker build -t registry.hatal.cc/instagram-pipeline/instagram-pipeline:0.1.0 .
docker push registry.hatal.cc/instagram-pipeline/instagram-pipeline:0.1.0
```

## Install

```bash
helm upgrade --install instagram-pipeline ./helm/instagram-pipeline \
  -n instagram-pipeline --create-namespace \
  --set image.auth.username='admin' \
  --set-string image.auth.password='<harbor-password>' \
  --set secrets.openaiApiKey='sk-...' \
  --set-string secrets.instagramAccessToken='IGQVJ...' \
  --set secrets.s3AccessKey='minio' \
  --set-string secrets.s3SecretKey='<minio-secret>' \
  --set-string secrets.authPassword='<api-password>' \
  --set-string secrets.authSecretKey="$(openssl rand -hex 32)" \
  --set-string config.instagram.igUserId='17841428303536831'
```

`image.tag` defaults to `.Chart.AppVersion` (`0.1.0`).

## Values

| Key | Default | Notes |
| --- | --- | --- |
| `image.registry` / `image.repository` / `image.tag` | `registry.hatal.cc` / `instagram-pipeline/instagram-pipeline` / `""` | tag defaults to `appVersion` |
| `image.auth.username` / `password` / `secretName` | `""` / `""` / `registry-secret` | set user+pass to create the pull Secret |
| `ingress.enabled` | `false` | exposes the API |
| `ingress.host` / `className` / `clusterIssuer` / `tlsSecretName` | `pipeline.hatal.cc` / `traefik` / `letsencrypt-prod` / `instagram-pipeline-tls` | |
| `persistence.enabled` / `storageClass` / `size` | `false` / `local-path` / `2Gi` | `false` = `emptyDir` |
| `resources` | small requests/limits | |
| `config.*` | placeholders | non-secret config → ConfigMap |
| `secrets.*` | placeholders | Secret → env vars (see below) |

Secret → env mapping:

| `secrets.*` | env var |
| --- | --- |
| `openaiApiKey` | `OPENAI_API_KEY` |
| `instagramAccessToken` | `INSTAGRAM_ACCESS_TOKEN` |
| `s3AccessKey` / `s3SecretKey` | `S3_ACCESS_KEY` / `S3_SECRET_KEY` |
| `authPassword` / `authSecretKey` | `AUTH_PASSWORD` / `AUTH_SECRET_KEY` |

Only `image`, `ingress`, `persistence`, `resources`, `secrets`, and `config` are
configurable; everything else (replicas, ports, security context, probes) is
fixed in the templates.

## Operations

```bash
kubectl -n instagram-pipeline get pods
kubectl -n instagram-pipeline logs deploy/instagram-pipeline-instagram-pipeline -f
kubectl -n instagram-pipeline port-forward svc/instagram-pipeline-instagram-pipeline 8000:8000
# Swagger: http://localhost:8000/docs   Health: /api/v1/health
```

Login to the API with `config.auth.username` / `secrets.authPassword`, then
`POST /api/v1/posts` (`publish=true`) to run the full pipeline.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ImagePullBackOff` | set `image.auth.username`/`password` (or ensure a `registry-secret` exists in the namespace) and that the Harbor project/image exists |
| `403`/config error at startup | the rendered `config.yaml` failed validation — check `secrets.*`/`config.*` (e.g. `auth.password` ≥ 8 chars, `auth.secretKey` ≥ 32) |
| Images 404 after a restart | `persistence.enabled=false` uses an ephemeral `emptyDir`; enable persistence or serve from S3 |
