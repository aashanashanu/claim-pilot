#!/usr/bin/env bash
# Ensures a shared S3 bucket exists for Terraform remote state, then runs
# `terraform init` against it (using S3 native state locking, no DynamoDB
# table required). Sourced by both CI and local deploy scripts so state
# persists across runs instead of being lost on ephemeral CI runners.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TF_DIR="infra/aws"
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
REGION="${REGION:-us-west-2}"
STATE_KEY="${TF_STATE_KEY:-claimpilot/aws-demo.tfstate}"

account_id="$(aws sts get-caller-identity --query Account --output text)"
bucket="${TF_STATE_BUCKET:-claimpilot-tfstate-${account_id}}"

if ! aws s3api head-bucket --bucket "$bucket" --region "$REGION" 2>/dev/null; then
  echo "Creating Terraform state bucket: $bucket"
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$bucket" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$bucket" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION"
  fi
  aws s3api put-bucket-versioning --bucket "$bucket" --region "$REGION" \
    --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption --bucket "$bucket" --region "$REGION" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-public-access-block --bucket "$bucket" --region "$REGION" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

terraform -chdir="$TF_DIR" init \
  -backend-config="bucket=$bucket" \
  -backend-config="key=$STATE_KEY" \
  -backend-config="region=$REGION" \
  -backend-config="use_lockfile=true"
