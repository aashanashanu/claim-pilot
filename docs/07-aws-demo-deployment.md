# AWS Demo Deployment Guide

This project is designed to run in a cost-optimized demo configuration using:

- AWS App Runner for the Python FastAPI API
- S3 + CloudFront for the React frontend
- ECR for container image storage
- Terraform for infrastructure provisioning

This keeps the architecture simple and cheap while still aligning with the project’s demo needs.

For a complete setup and runbook, see [docs/08-end-to-end-demo-guide.md](docs/08-end-to-end-demo-guide.md).

## Why this stack

- App Runner: minimal infrastructure and quick setup for a containerized Python API
- S3 + CloudFront: cheapest way to host a static React dashboard globally
- ECR: simple image registry for the backend container
- Terraform: repeatable and easy to tear down after the demo

## Files added

- Dockerfile
- scripts/deploy-demo.sh
- infra/aws/main.tf
- infra/aws/variables.tf
- infra/aws/outputs.tf
- infra/aws/modules/*
- infra/aws/terraform.tfvars.example

## Prerequisites

1. AWS CLI installed and authenticated
2. Terraform installed
3. Docker installed
4. A unique S3 bucket name for the frontend

Copy the example vars file before the first deploy and fill in the runtime secret JSON that Terraform will store in Secrets Manager:

```bash
cp infra/aws/terraform.tfvars.example infra/aws/terraform.tfvars
```

## Backend container build

```bash
docker build -t claimpilot-backend-demo .
```

## Demo deployment script

```bash
chmod +x scripts/deploy-demo.sh
./scripts/deploy-demo.sh
```

The current deployment model is Terraform-owned end to end: the script only calls `terraform init` and `terraform apply`, and Terraform triggers the artifact build/publish steps itself.

## Terraform deployment

```bash
terraform -chdir=infra/aws init
terraform -chdir=infra/aws plan
terraform -chdir=infra/aws apply
```

The outputs will provide:

- frontend URL
- backend URL
- ECR repository URL

## Frontend env config

Set the frontend API URL in the deployment environment:

```bash
VITE_API_BASE=https://<your-app-runner-url>
```

The deployed frontend should call the App Runner backend URL for all scenario actions.

## Strands + Bedrock runtime configuration

The App Runner backend reads AWS credentials and the Bedrock model from the runtime environment. In the Terraform setup, these values are stored in AWS Secrets Manager and injected into the service at runtime:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_REGION`
- `CLAIMPILOT_MODEL_ID`

The application logic in `src/claimpilot/agent_runtime.py` checks for these values and uses the real Strands/Bedrock path when they are present. If credentials are missing, the backend fails fast with a `STRANDS_NOT_CONFIGURED` health response so deployment problems are obvious.

Terraform now stores all runtime values in a single Secrets Manager JSON secret named `claimpilot/runtime-config`, which the App Runner service injects as `CLAIMPILOT_RUNTIME_SECRETS_JSON`. That JSON should include AWS credentials, the Bedrock model ID, Gmail OAuth JSON blobs, the target inbox address, and the Gmail query.

The Strands SDK is installed inside the backend container during the Docker build step via `pip install -e .` from `pyproject.toml` dependencies, and that container image is pushed to ECR and run by App Runner.

For the full infra map and component purposes, see [docs/09-aws-infra-architecture.md](docs/09-aws-infra-architecture.md).

## Cost optimization notes

- Use only one region
- Use CloudFront PriceClass_100
- Keep the backend to the smallest App Runner instance size
- Use a single S3 bucket and static hosting
- Avoid Lambda or DynamoDB unless the demo needs a richer backend later
- In local and demo-only validation, prefer the test suite and mocked adapters rather than inventing a runtime fallback.

## Secret Management Pattern

Best practice for this repository is one Terraform-managed runtime secret JSON object rather than many manually created AWS secrets. That keeps the deployment repeatable and means the only manual step is supplying the secret values in `infra/aws/terraform.tfvars` before `terraform apply`.

## Clean-up

```bash
terraform -chdir=infra/aws destroy
```

This removes the infrastructure created for the demo.
