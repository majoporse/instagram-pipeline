# minio-tenant

MinIO deployed through the **official MinIO Operator** (the provider) with a
**Tenant** config, instead of a hand-rolled StatefulSet.

The MinIO Operator was archived on 2026-03-20 (and the CE server repo in Feb
2026), so everything here is frozen/pinned — but it is the sanctioned way to run
MinIO on Kubernetes.

```
helm/minio-tenant/
  values-tenant.yaml     # config for the official minio-operator/tenant chart
  provisioning-job.yaml  # bucket policy (anonymous GET on posts/*) + 7d expiry
```

## 1. Install the operator (once per cluster)

```bash
kubectl kustomize github.com/minio/operator\?ref=v7.1.1 | kubectl apply -f -
```

## 2. Install the tenant

```bash
kubectl create namespace instagram-pipeline-media
helm install minio minio-operator/tenant \
  -n instagram-pipeline-media \
  -f helm/minio-tenant/values-tenant.yaml
```

This creates the `Tenant` CR, the `minio-credentials` Secret, the `minio` S3
service, and two Ingresses (Traefik + cert-manager):

- **S3 API**: `https://s3.pipeline.hatal.cc`
- **Console**: `https://minio-console.pipeline.hatal.cc`

Edit `secretKey`, `size`, and `storageClassName` in `values-tenant.yaml` first.
Both hostnames need DNS records pointing at the cluster's ingress.

## 3. Apply the bucket policy + lifecycle

The tenant chart only creates the bucket. Run the provisioning job to allow
anonymous `GET` **only** under `posts/*` and expire objects after 7 days.

**Run it in the tenant's namespace.** It reaches the tenant's S3 Service by its
short name. With the shipped `values-tenant.yaml`: tenant = `minio`, so the S3
Service is `minio` on **port 80** (http, since `requestAutoCert: false`) and the
console Service is `minio-console` on 9090.

```bash
# a changed Job spec can't be applied over an existing Job
kubectl -n instagram-pipeline-media delete job minio-provision --ignore-not-found

kubectl apply -n instagram-pipeline-media -f helm/minio-tenant/provisioning-job.yaml
kubectl -n instagram-pipeline-media wait --for=condition=complete job/minio-provision --timeout=330s
kubectl -n instagram-pipeline-media logs job/minio-provision
```

The job uses `bitnamilegacy/minio-client:latest` for `mc` — MinIO removed
`minio/mc` from Docker Hub when the CE repo was archived. If it fails, the logs
print the endpoint it tried; confirm the real Service name/port/namespace:

```bash
kubectl get tenant -A
kubectl get svc -A | grep -i minio
kubectl -n instagram-pipeline-media get svc minio -o jsonpath='{range .spec.ports[*]}{.name}{" "}{.port}{"\n"}{end}'
```

## 4. Wire the app chart

```yaml
# helm/instagram-pipeline values
config:
  s3:
    # Must be Meta-reachable: URL = {endpointUrl}/{bucket}/{key}.
    endpointUrl: "https://s3.pipeline.hatal.cc"
    bucket: "instagram-pipeline"
secrets:
  s3AccessKey: "minio"          # tenant.configSecret.accessKey
  s3SecretKey: "<secretKey>"
```

## Verify

```bash
kubectl -n instagram-pipeline-media get tenant,pods,svc,ingress
curl -I https://s3.pipeline.hatal.cc/instagram-pipeline/posts/<post_id>/<post_id>-0.jpg
```

**Console** (log in with the root credentials from the Secret):

```bash
kubectl -n instagram-pipeline-media get secret minio-credentials -o jsonpath='{.data.config\.env}' | base64 -d
# open https://minio-console.pipeline.hatal.cc
```

If DNS/ingress isn't ready yet, port-forward instead:

```bash
kubectl -n instagram-pipeline-media port-forward svc/minio-console 9090:9090   # http-console
# open http://localhost:9090
``

## Notes

- Standalone: `servers: 1` (no replicas). The operator wants ≥4 volumes, so the
  pool uses `volumesPerServer: 4` (4 × 5Gi PVCs on one node).
- Bucket names, retention, and the public prefix are hardcoded to this project
  in `provisioning-job.yaml`; adjust if you rename them.
- If you rename the tenant or namespace, update the service DNS and Secret name
  in `provisioning-job.yaml` and the app values above.
