variable "kubeconfig_path" {
  description = "Optional kubeconfig path. Leave null to use the provider default."
  type        = string
  default     = null
}

variable "kube_context" {
  description = "Optional kubeconfig context. Leave null to use the active context."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace where the serving platform is deployed."
  type        = string
  default     = "mini-llm-serving"
}

variable "argocd_namespace" {
  description = "Namespace where Argo CD is installed."
  type        = string
  default     = "argocd"
}

variable "repo_url" {
  description = "Git repository URL watched by Argo CD."
  type        = string
  default     = "https://github.com/ictup/Mini_LLM_Serving_Platform.git"
}

variable "target_revision" {
  description = "Git revision watched by Argo CD."
  type        = string
  default     = "main"
}

variable "gateway_image" {
  description = "Gateway and mock backend image used by the Helm chart."
  type        = string
  default     = "ghcr.io/ictup/mini-llm-serving-platform:main"
}

variable "image_pull_policy" {
  description = "Image pull policy for Gateway and mock backend containers."
  type        = string
  default     = "IfNotPresent"
}

variable "deploy_vllm" {
  description = "When true, deploy the vLLM GPU stack. When false, deploy mock mode."
  type        = bool
  default     = false
}

variable "create_namespace" {
  description = "Create the serving namespace before Argo CD syncs the Helm release."
  type        = bool
  default     = true
}

variable "create_placeholder_secrets" {
  description = "Create local placeholder Secrets. Prefer External Secrets for shared clusters."
  type        = bool
  default     = false
}

variable "gateway_api_keys" {
  description = "Client API keys used only when create_placeholder_secrets is true."
  type        = list(string)
  default     = ["replace-me"]
  sensitive   = true
}

variable "vllm_api_key" {
  description = "Gateway-to-vLLM API key used only when create_placeholder_secrets is true."
  type        = string
  default     = "replace-me"
  sensitive   = true
}

variable "hugging_face_hub_token" {
  description = "Optional Hugging Face token used only when create_placeholder_secrets is true."
  type        = string
  default     = ""
  sensitive   = true
}

variable "gateway_min_replicas" {
  description = "Minimum Gateway replicas when Helm autoscaling is enabled."
  type        = number
  default     = 1
}

variable "gateway_max_replicas" {
  description = "Maximum Gateway replicas when Helm autoscaling is enabled."
  type        = number
  default     = 3
}

variable "vllm_image" {
  description = "vLLM OpenAI-compatible image."
  type        = string
  default     = "vllm/vllm-openai:v0.8.5.post1"
}

variable "vllm_model" {
  description = "Hugging Face model served by vLLM."
  type        = string
  default     = "Qwen/Qwen2.5-0.5B-Instruct"
}

variable "vllm_dtype" {
  description = "vLLM dtype argument."
  type        = string
  default     = "float16"
}

variable "vllm_max_model_len" {
  description = "Maximum vLLM context length."
  type        = number
  default     = 4096
}

variable "vllm_gpu_memory_utilization" {
  description = "Fraction of GPU memory vLLM can target."
  type        = number
  default     = 0.75
}

variable "vllm_swap_space" {
  description = "vLLM CPU swap space in GiB."
  type        = number
  default     = 1
}

variable "vllm_gpu_count" {
  description = "Number of GPUs requested by the vLLM pod."
  type        = number
  default     = 1
}

variable "dcgm_exporter_image" {
  description = "NVIDIA DCGM exporter image used when deploy_vllm is true."
  type        = string
  default     = "nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04"
}
