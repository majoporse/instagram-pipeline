{{- define "instagram-pipeline.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "instagram-pipeline.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "instagram-pipeline.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* ConfigMap holding the non-secret config.yaml. */}}
{{- define "instagram-pipeline.configMapName" -}}
{{- include "instagram-pipeline.fullname" . -}}
{{- end -}}

{{/* Secret holding the secret settings, injected as env vars. */}}
{{- define "instagram-pipeline.secretName" -}}
{{- printf "%s-secret" (include "instagram-pipeline.fullname" .) -}}
{{- end -}}

{{- define "instagram-pipeline.registrySecretName" -}}
{{- default "registry-secret" .Values.image.auth.secretName -}}
{{- end -}}

{{/* dockerconfigjson payload for the configured registry credentials. */}}
{{- define "instagram-pipeline.dockerconfigjson" -}}
{{- $auth := printf "%s:%s" .Values.image.auth.username .Values.image.auth.password | b64enc -}}
{{- printf "{\"auths\":{\"%s\":{\"username\":%q,\"password\":%q,\"auth\":%q}}}" .Values.image.registry .Values.image.auth.username .Values.image.auth.password $auth -}}
{{- end -}}

{{/* Non-secret config.yaml. Secrets are injected as env vars (see config.py). */}}
{{- define "instagram-pipeline.config" -}}
openai:
  model: {{ .Values.config.openai.model | quote }}
{{- if .Values.config.openai.baseUrl }}
  base_url: {{ .Values.config.openai.baseUrl | quote }}
{{- end }}
instagram:
  ig_user_id: {{ .Values.config.instagram.igUserId | quote }}
{{- if .Values.config.instagram.graphApiVersion }}
  graph_api_version: {{ .Values.config.instagram.graphApiVersion | quote }}
{{- end }}
s3:
  endpoint_url: {{ .Values.config.s3.endpointUrl | quote }}
  bucket: {{ .Values.config.s3.bucket | quote }}
{{- if .Values.config.s3.region }}
  region: {{ .Values.config.s3.region | quote }}
{{- end }}
{{- if .Values.config.s3.prefix }}
  prefix: {{ .Values.config.s3.prefix | quote }}
{{- end }}
auth:
  username: {{ .Values.config.auth.username | quote }}
  cookie_secure: {{ .Values.config.auth.cookieSecure }}
{{- if .Values.config.auth.cookieDomain }}
  cookie_domain: {{ .Values.config.auth.cookieDomain | quote }}
{{- end }}
caption:
  hashtags:
{{ toYaml .Values.config.caption.hashtags | indent 4 }}
upload:
  dry_run: {{ .Values.config.upload.dryRun }}
  carousel: {{ .Values.config.upload.carousel }}
{{- end -}}
