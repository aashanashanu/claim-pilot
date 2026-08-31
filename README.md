# ClaimPilot

ClaimPilot is a demo-friendly post-purchase exception handling system that watches orders, auto-resolves safe issues, and asks for user input only when required.

This repository contains the MVP backend, a React demo dashboard, and the AWS deployment setup needed to run the project end-to-end without heavy infrastructure.

## Current Implementation Status

- Event-driven core pipeline with `OrderDetected`, `StatusChanged`, `AutoResolve`, and `NeedsDecision`
- Decision table for the three locked MVP beats: price drop, damaged item, return window closing
- React-powered desktop/demo dashboard connected to the backend API
- Gmail-backed storefront demo flow that sends real order/status mail and exposes human decision capture
- FastAPI API for live scenario triggering and audit snapshot reads
- Cost-optimized AWS deployment path using App Runner, S3, CloudFront, and ECR
- Focused automated tests for the backend demo service and dashboard logic

## Architecture Overview

- Backend: Python FastAPI app with in-memory event pipeline
- Frontend: React + Vite app served from S3 + CloudFront
- AWS runtime: App Runner for the API, CloudFront + S3 for UI
- Demo mode: No production data stores or expensive orchestration required

## Documentation Pack

- Architecture diagram: [docs/01-architecture-diagram.md](docs/01-architecture-diagram.md)
- Phased plan: [docs/02-phased-implementation-plan.md](docs/02-phased-implementation-plan.md)
- Testing strategy: [docs/03-testing-strategy.md](docs/03-testing-strategy.md)
- Submission checklist: [docs/04-submission-requirements.md](docs/04-submission-requirements.md)
- Phase 0 Step 1 artifact: [docs/05-phase-0-step-1-scope-freeze.md](docs/05-phase-0-step-1-scope-freeze.md)
- Demo and judging playbook: [docs/06-demo-and-judging-playbook.md](docs/06-demo-and-judging-playbook.md)
- AWS demo deployment guide: [docs/07-aws-demo-deployment.md](docs/07-aws-demo-deployment.md)
- End-to-end demo guide: [docs/08-end-to-end-demo-guide.md](docs/08-end-to-end-demo-guide.md)
- AWS infrastructure architecture: [docs/09-aws-infra-architecture.md](docs/09-aws-infra-architecture.md)
- Rules gap remediation plan: [docs/10-rules-gap-remediation-plan.md](docs/10-rules-gap-remediation-plan.md)

## Quick Start

### Local backend + dashboard

```bash
cd /Users/aashanashanu/Documents/projects/self/claim-pilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m pytest
uvicorn claimpilot.api:app --host 0.0.0.0 --port 8000
```

Then, in a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Set the frontend environment if needed:

```bash
cp frontend/.env.example frontend/.env
```

Default API URL:

```bash
VITE_API_BASE=http://localhost:8000
```

For the live runtime, configure Gmail send/read credentials and the target inbox before starting the API:

```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export AWS_REGION=us-west-2
export GMAIL_CREDENTIALS_FILE=/absolute/path/to/google-client-secret.json
export GMAIL_TOKEN_FILE=/absolute/path/to/.gmail-token.json
export CLAIMPILOT_GMAIL_TARGET_ADDRESS=your-demo-inbox@example.com
```

Follow [docs/08-end-to-end-demo-guide.md](docs/08-end-to-end-demo-guide.md) for a fresh demo environment and a full run from seed to human decision capture.

Phase 2 Gmail ingestion endpoint:

```bash
# Required once: set OAuth client credentials and token file paths
export GMAIL_CREDENTIALS_FILE=/absolute/path/to/google-client-secret.json
export GMAIL_TOKEN_FILE=/absolute/path/to/.gmail-token.json

# Ingest real Gmail inbox messages (read-only scope). This is optional backfill/debug only because the backend now watches Gmail automatically.
curl -X POST "http://localhost:8000/integrations/email/gmail/ingest?user_id=user-demo&max_results=3"

# Validate Gmail token/dependency readiness
curl -X GET "http://localhost:8000/health/gmail"
```

Optional Gmail filter query (defaults to `newer_than:14d`):

```bash
export CLAIMPILOT_GMAIL_QUERY='newer_than:7d (subject:(order OR shipped OR delivery OR receipt))'
```

### AWS demo deployment

Prerequisites:

```bash
export AWS_REGION=us-east-1
```

Install Terraform and make sure the AWS CLI is authenticated for the target account.

Then run:

```bash
chmod +x scripts/deploy-demo.sh
./scripts/deploy-demo.sh
./scripts/smoke-aws-demo.sh
```

CI deployment is also available via GitHub Actions using repo secrets. See [docs/07-aws-demo-deployment.md](docs/07-aws-demo-deployment.md) for required secret names and workflow details.

Before deploying, copy the Terraform example vars file and fill in the runtime secret JSON that Terraform will store in Secrets Manager:

```bash
cp infra/aws/terraform.tfvars.example infra/aws/terraform.tfvars
```

Then edit [infra/aws/terraform.tfvars](infra/aws/terraform.tfvars) with the real AWS, Gmail, and Bedrock values.

Or use Terraform directly:

```bash
terraform -chdir=infra/aws init
terraform -chdir=infra/aws apply
```

Terraform owns the full deployment: it creates the ECR repo, Secrets Manager runtime JSON, App Runner backend, CloudFront frontend, and the artifact publish steps that build and sync the frontend/backend.

After apply, run the smoke script to validate backend health, Gmail readiness, one-click runbook execution, storefront reachability, and frontend URL availability using Terraform outputs.

To trigger the deterministic full demo sequence (phase 4 surface), call:

```bash
curl -X POST https://<your-app-runner-url>/demo/runbook
```

## AWS Deployment Architecture

This is the recommended demo-ready setup:

- S3 + CloudFront: React UI
- App Runner: FastAPI backend
- ECR: container image registry
- Terraform: infrastructure definition and teardown
- Secrets Manager: Strands/Bedrock credentials injection

This is intentionally smaller and cheaper than a full ECS + RDS + Lambda architecture while still being realistic enough for a live demo.

The App Runner container loads the AWS credentials from AWS Secrets Manager, and the Strands runtime uses them to call Bedrock when `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` are present. This build requires a configured Strands runtime and does not use a deterministic rules fallback.

## Project Phases

- Phase 0: Rules lock and scope freeze
- Phase 1: Core runtime and decision table
- Phase 2: Gmail ingestion, storefront mail generation, and carrier tracking
- Phase 3: Resolution, notification, and human decision capture
- Phase 4: Demo surface and operator workflow
- Phase 5: Testing and hardening
- Phase 6: Submission packaging
- Phase 7: Final gate and submit

## Notes

- Local and deployed demo runs require Strands runtime dependencies and AWS credentials for Bedrock access.
- Real Strands + Bedrock integration is mandatory in this build.
- This repo is intentionally optimized for a hackathon demo and a low-cost cloud deployment path.
- Structured, redacted JSON telemetry is emitted for ingestion, tracking, decision routing, and decision capture.
- Use `./scripts/validate-local.sh` for one-command backend tests + focused integration checks + frontend build.
