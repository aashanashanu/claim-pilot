#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
ECR_REPO="${ECR_REPO:-claimpilot-backend-demo}"
FRONTEND_BUCKET="${FRONTEND_BUCKET:-claimpilot-demo-frontend}"

if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  echo "AWS_ACCOUNT_ID is required. Export it or set it in your shell before running this script."
  exit 1
fi

cd frontend
npm install
npm run build
cd "$ROOT_DIR"

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION"

IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"
docker build -t "$ECR_REPO:latest" .
docker tag "$ECR_REPO:latest" "$IMAGE_URI"
docker push "$IMAGE_URI"

aws s3 mb "s3://$FRONTEND_BUCKET" --region "$AWS_REGION" --acl private 2>/dev/null || true
aws s3 sync frontend/dist "s3://$FRONTEND_BUCKET" --delete

printf '\nDeployment instructions:\n'
printf '1. Point the frontend env to the backend App Runner URL after Terraform creates it.\n'
printf '2. Run: terraform -chdir=infra/aws init && terraform -chdir=infra/aws apply\n'
printf '3. Use the CloudFront URL for the demo UI and the App Runner URL for the backend.\n'
