# Terraform IaC Skeleton

This root module manages the cluster-side entry point for the serving platform:

- the serving namespace,
- optional local placeholder Secrets for lab clusters,
- one Argo CD `Application` that syncs `deploy/helm` from this repository.

It intentionally does not create a Kubernetes cluster. Cluster creation differs
across EKS, AKS, GKE, on-prem, and local clusters, so this module starts at the
common boundary where a kubeconfig and Argo CD already exist.

## Files

| File | Purpose |
| --- | --- |
| `versions.tf` | Terraform and provider constraints. |
| `variables.tf` | Cluster, image, secret, and vLLM inputs. |
| `main.tf` | Namespace, optional Secrets, and Argo CD Application. |
| `outputs.tf` | Application name, namespace, mode, and image outputs. |
| `terraform.tfvars.example` | Local example values without real secrets. |

## Usage

```bash
cd deploy/terraform
terraform init
terraform plan
terraform apply
```

For vLLM GPU mode:

```bash
terraform plan -var="deploy_vllm=true"
terraform apply -var="deploy_vllm=true"
```

## Secret Handling

By default, this module expects `gateway-secret` and, for vLLM mode,
`vllm-secret` to already exist in the target namespace. That is the preferred
path for shared clusters using External Secrets, Vault, cloud secret managers,
or a platform bootstrap process.

For a disposable lab cluster, set:

```hcl
create_placeholder_secrets = true
gateway_api_keys           = ["replace-me"]
vllm_api_key               = "replace-me"
```

Those values will be written to Terraform state. Do not use this mode with real
production secrets unless your backend state is encrypted and access-controlled.

## Relationship to GitOps

The module creates an Argo CD Application equivalent to the static examples in
`deploy/gitops`, but keeps cluster-specific values in Terraform variables. The
Application still points to `deploy/helm`, so Helm remains the single deployment
template.
