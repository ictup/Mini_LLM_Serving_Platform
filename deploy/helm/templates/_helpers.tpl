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
