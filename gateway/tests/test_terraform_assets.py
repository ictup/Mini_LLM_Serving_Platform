from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_DIR = ROOT / "deploy/terraform"


def read_terraform_file(name: str) -> str:
    return (TERRAFORM_DIR / name).read_text(encoding="utf-8")


def test_terraform_root_module_has_expected_files() -> None:
    for file_name in [
        "versions.tf",
        "variables.tf",
        "main.tf",
        "outputs.tf",
        "terraform.tfvars.example",
        "README.md",
    ]:
        assert (TERRAFORM_DIR / file_name).exists()


def test_terraform_provider_and_state_files_are_configured_safely() -> None:
    versions = read_terraform_file("versions.tf")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert 'required_version = ">= 1.6.0"' in versions
    assert 'source  = "hashicorp/kubernetes"' in versions
    assert 'version = "~> 2.35"' in versions
    assert ".terraform/" in gitignore
    assert "*.tfstate" in gitignore
    assert "*.tfvars" in gitignore
    assert "!*.tfvars.example" in gitignore


def test_terraform_variables_keep_real_secrets_out_of_git() -> None:
    variables = read_terraform_file("variables.tf")
    example = read_terraform_file("terraform.tfvars.example")

    assert 'variable "create_placeholder_secrets"' in variables
    assert "default     = false" in variables
    assert 'variable "gateway_api_keys"' in variables
    assert 'variable "vllm_api_key"' in variables
    assert 'variable "hugging_face_hub_token"' in variables
    assert "sensitive   = true" in variables
    assert 'gateway_api_keys = ["replace-me"]' in example
    assert 'vllm_api_key     = "replace-me"' in example
    assert "Do not commit terraform.tfvars" in example


def test_terraform_manages_argocd_application_for_helm_chart() -> None:
    main = read_terraform_file("main.tf")

    assert 'resource "kubernetes_namespace_v1" "serving"' in main
    assert 'resource "kubernetes_manifest" "argocd_application"' in main
    assert 'apiVersion = "argoproj.io/v1alpha1"' in main
    assert 'kind       = "Application"' in main
    assert 'path           = "deploy/helm"' in main
    assert "valuesObject = local.helm_values" in main
    assert 'server    = "https://kubernetes.default.svc"' in main
    assert '"CreateNamespace=true"' in main
    assert "prune    = true" in main
    assert "selfHeal = true" in main


def test_terraform_values_cover_mock_and_vllm_modes() -> None:
    main = read_terraform_file("main.tf")
    variables = read_terraform_file("variables.tf")

    assert 'app_name = var.deploy_vllm ? "mini-llm-serving-vllm"' in main
    assert '"mini-llm-serving-mock"' in main
    assert "mockBackend" in main
    assert "enabled         = !var.deploy_vllm" in main
    assert "existingSecretName         = var.deploy_vllm ? \"vllm-secret\" : \"\"" in main
    assert "modelAliasesJson   = local.model_aliases_json" in main
    assert "tokenizerProfilesJson = local.tokenizer_profiles_json" in main
    assert 'default     = "Qwen/Qwen2.5-0.5B-Instruct"' in variables
    assert 'default     = "vllm/vllm-openai:v0.8.5.post1"' in variables


def test_terraform_readme_documents_boundaries_and_usage() -> None:
    readme = read_terraform_file("README.md")

    assert "It intentionally does not create a Kubernetes cluster" in readme
    assert "terraform init" in readme
    assert 'terraform plan -var="deploy_vllm=true"' in readme
    assert "External Secrets" in readme
    assert "Those values will be written to Terraform state" in readme
