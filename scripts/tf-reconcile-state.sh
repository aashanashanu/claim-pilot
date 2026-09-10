#!/usr/bin/env bash
# Imports any AWS resources that already exist (e.g. left over from a prior CI
# run whose Terraform state was not persisted) into the local state before
# `terraform apply` runs, so create calls don't fail with "already exists".
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TF_DIR="infra/aws"
REGION="${AWS_REGION:?AWS_REGION must be set}"
BUCKET="${FRONTEND_BUCKET_NAME:?FRONTEND_BUCKET_NAME must be set}"
ECR_REPO="${ECR_REPOSITORY_NAME:?ECR_REPOSITORY_NAME must be set}"
SECRET_NAME="${RUNTIME_SECRET_NAME:?RUNTIME_SECRET_NAME must be set}"
APPRUNNER_SERVICE="${APP_RUNNER_SERVICE_NAME:?APP_RUNNER_SERVICE_NAME must be set}"

state_has() {
  terraform -chdir="$TF_DIR" state list 2>/dev/null | grep -qxF "$1"
}

import_resource() {
  local addr="$1" id="$2"
  if [[ -z "$id" || "$id" == "None" || "$id" == "null" ]]; then
    return 0
  fi
  if state_has "$addr"; then
    echo "skip (already in state): $addr"
    return 0
  fi
  echo "importing $addr -> $id"
  terraform -chdir="$TF_DIR" import "$addr" "$id" || echo "warn: import failed for $addr, apply will attempt to create it"
}

# S3 bucket
if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
  import_resource "module.frontend.aws_s3_bucket.this" "$BUCKET"
fi

# ECR repository
if aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" >/dev/null 2>&1; then
  import_resource "module.ecr.aws_ecr_repository.this" "$ECR_REPO"
fi

# Secrets Manager secret
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" >/dev/null 2>&1; then
  import_resource "module.secrets.aws_secretsmanager_secret.runtime" "$SECRET_NAME"
fi

# CloudFront Origin Access Control (name is hardcoded in modules/frontend/main.tf)
oac_id="$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='claimpilot-frontend-oac'].Id | [0]" \
  --output text 2>/dev/null || true)"
import_resource "module.frontend.aws_cloudfront_origin_access_control.this" "$oac_id"

# CloudFront distribution (matched by its S3 origin domain name)
dist_id="$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Origins.Items[0].DomainName, '${BUCKET}')].Id | [0]" \
  --output text 2>/dev/null || true)"
import_resource "module.frontend.aws_cloudfront_distribution.this" "$dist_id"

# IAM roles used by App Runner
if aws iam get-role --role-name claimpilot-apprunner-ecr-role >/dev/null 2>&1; then
  import_resource "module.apprunner.aws_iam_role.ecr" "claimpilot-apprunner-ecr-role"
fi
if aws iam get-role --role-name claimpilot-apprunner-instance-role >/dev/null 2>&1; then
  import_resource "module.apprunner.aws_iam_role.instance" "claimpilot-apprunner-instance-role"
fi

# App Runner service
apprunner_arn="$(aws apprunner list-services \
  --query "ServiceSummaryList[?ServiceName=='${APPRUNNER_SERVICE}'].ServiceArn | [0]" \
  --output text --region "$REGION" 2>/dev/null || true)"
import_resource "module.apprunner.aws_apprunner_service.this" "$apprunner_arn"

echo "Reconciliation complete."
