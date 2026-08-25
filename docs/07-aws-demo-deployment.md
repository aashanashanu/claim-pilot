# AWS Demo Deployment Guide

This project is designed to run in a cost-optimized demo configuration using:

- AWS App Runner for the Python FastAPI API
- S3 + CloudFront for the React frontend
- ECR for container image storage
- Terraform for infrastructure provisioning

This keeps the architecture simple and cheap while still aligning with the project’s demo needs.

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

## Prerequisites

1. AWS CLI installed and authenticated
2. Terraform installed
3. Docker installed
4. A unique S3 bucket name for the frontend
5. AWS account ID exported as AWS_ACCOUNT_ID

Example:

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-west-2
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

This script builds the frontend, pushes the backend container to ECR, and syncs the React build to S3.

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

The application logic in `src/claimpilot/agent_runtime.py` checks for these values and uses the real Strands/Bedrock path when they are present. If credentials are missing, the app falls back to the deterministic rules engine so the project still runs in local or demo-only mode.

## Cost optimization notes

- Use only one region
- Use CloudFront PriceClass_100
- Keep the backend to the smallest App Runner instance size
- Use a single S3 bucket and static hosting
- Avoid Lambda or DynamoDB unless the demo needs a richer backend later

## Clean-up

```bash
terraform -chdir=infra/aws destroy
```

This removes the infrastructure created for the demo.
