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
