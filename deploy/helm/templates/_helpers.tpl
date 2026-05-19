{{- define "mini-llm.name" -}}
mini-llm-serving-platform
{{- end -}}

{{- define "mini-llm.labels" -}}
app.kubernetes.io/part-of: mini-llm-serving-platform
app.kubernetes.io/managed-by: Helm
{{- end -}}

{{- define "mini-llm.componentLabels" -}}
{{ include "mini-llm.labels" . }}
app.kubernetes.io/name: {{ .name }}
{{- end -}}

{{- define "mini-llm.gatewaySecretName" -}}
{{- if .Values.gateway.existingSecretName -}}
{{ .Values.gateway.existingSecretName }}
{{- else -}}
gateway-secret
{{- end -}}
{{- end -}}

{{- define "mini-llm.vllmSecretName" -}}
{{- if .Values.vllm.existingSecretName -}}
{{ .Values.vllm.existingSecretName }}
{{- else -}}
vllm-secret
{{- end -}}
{{- end -}}
