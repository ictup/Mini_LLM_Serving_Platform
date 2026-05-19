output "argocd_application_name" {
  description = "Argo CD Application managed by this Terraform root module."
  value       = local.app_name
}

output "namespace" {
  description = "Serving namespace targeted by the Argo CD Application."
  value       = var.namespace
}

output "deployment_mode" {
  description = "Selected deployment mode."
  value       = var.deploy_vllm ? "vllm" : "mock"
}

output "gateway_image" {
  description = "Gateway image referenced by Helm values."
  value       = var.gateway_image
}
