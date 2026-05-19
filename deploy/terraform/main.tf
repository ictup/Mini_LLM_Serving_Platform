provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

locals {
  app_name = var.deploy_vllm ? "mini-llm-serving-vllm" : "mini-llm-serving-mock"

  common_labels = {
    "app.kubernetes.io/name"       = "mini-llm-serving"
    "app.kubernetes.io/part-of"    = "mini-llm-serving-platform"
    "app.kubernetes.io/managed-by" = "terraform"
  }

  model_aliases_json = var.deploy_vllm ? jsonencode({
    "qwen-small" = var.vllm_model
  }) : jsonencode({
    "mock"       = "mock"
    "qwen-small" = "mock"
  })

  tokenizer_profiles_json = var.deploy_vllm ? jsonencode({
    "qwen-small"      = "qwen2"
    (var.vllm_model) = "qwen2"
  }) : jsonencode({
    "mock"       = "estimated"
    "qwen-small" = "estimated"
  })

  helm_values = {
    namespace = {
      create = true
      name   = var.namespace
    }

    gateway = {
      image              = var.gateway_image
      imagePullPolicy    = var.image_pull_policy
      existingSecretName = "gateway-secret"
      modelAliasesJson   = local.model_aliases_json
      rateLimit = {
        tokenizerProfilesJson = local.tokenizer_profiles_json
      }
      autoscaling = {
        enabled     = true
        minReplicas = var.gateway_min_replicas
        maxReplicas = var.gateway_max_replicas
      }
    }

    mockBackend = {
      enabled         = !var.deploy_vllm
      image           = var.gateway_image
      imagePullPolicy = var.image_pull_policy
    }

    prometheus = {
      enabled = true
      alerting = {
        enabled = true
      }
    }

    vllm = {
      enabled                    = var.deploy_vllm
      image                      = var.vllm_image
      existingSecretName         = var.deploy_vllm ? "vllm-secret" : ""
      model                      = var.vllm_model
      dtype                      = var.vllm_dtype
      maxModelLen                = var.vllm_max_model_len
      gpuMemoryUtilization       = var.vllm_gpu_memory_utilization
      swapSpace                  = var.vllm_swap_space
      gpu                        = var.vllm_gpu_count
      huggingFaceHubToken        = ""
      apiKey                     = ""
    }
  }
}

resource "kubernetes_namespace_v1" "serving" {
  count = var.create_namespace ? 1 : 0

  metadata {
    name   = var.namespace
    labels = local.common_labels
  }
}

resource "kubernetes_secret_v1" "gateway" {
  count = var.create_placeholder_secrets ? 1 : 0

  metadata {
    name      = "gateway-secret"
    namespace = var.namespace
    labels    = local.common_labels
  }

  type = "Opaque"

  data = {
    API_KEYS     = join(",", var.gateway_api_keys)
    VLLM_API_KEY = var.vllm_api_key
  }

  depends_on = [kubernetes_namespace_v1.serving]
}

resource "kubernetes_secret_v1" "vllm" {
  count = var.create_placeholder_secrets && var.deploy_vllm ? 1 : 0

  metadata {
    name      = "vllm-secret"
    namespace = var.namespace
    labels    = local.common_labels
  }

  type = "Opaque"

  data = {
    VLLM_API_KEY           = var.vllm_api_key
    HUGGING_FACE_HUB_TOKEN = var.hugging_face_hub_token
  }

  depends_on = [kubernetes_namespace_v1.serving]
}

resource "kubernetes_manifest" "argocd_application" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = local.app_name
      namespace = var.argocd_namespace
      labels    = local.common_labels
    }
    spec = {
      project = "default"
      source = {
        repoURL        = var.repo_url
        targetRevision = var.target_revision
        path           = "deploy/helm"
        helm = {
          releaseName  = "mini-llm"
          valuesObject = local.helm_values
        }
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = var.namespace
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true",
        ]
      }
    }
  }

  depends_on = [
    kubernetes_namespace_v1.serving,
    kubernetes_secret_v1.gateway,
    kubernetes_secret_v1.vllm,
  ]
}
