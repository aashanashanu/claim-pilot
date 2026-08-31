#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TF_VARS_FILE="${CLAIMPILOT_TERRAFORM_VARS_FILE:-infra/aws/terraform.tfvars}"

if [[ ! -f "$TF_VARS_FILE" ]]; then
  echo "Terraform var file not found at $TF_VARS_FILE. Copy infra/aws/terraform.tfvars.example and fill in the secret values."
  exit 1
fi

TF_VARS_FILE="$(cd "$(dirname "$TF_VARS_FILE")" && pwd)/$(basename "$TF_VARS_FILE")"

terraform -chdir=infra/aws init
terraform -chdir=infra/aws apply -var-file="$TF_VARS_FILE"

printf '\nDeployment complete. Use the Terraform outputs for the CloudFront and App Runner URLs.\n'
