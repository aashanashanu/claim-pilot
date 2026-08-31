# End-to-End Demo Guide

This guide is the complete runbook for preparing and demonstrating ClaimPilot on AWS. It includes detailed infrastructure setup, Gmail credential creation, runtime secret wiring, pre-demo checks, demo data preparation, and a time-boxed live script for a video of at most 5 minutes.

## What This Demo Covers

- Gmail-backed order creation from the storefront demo.
- Real inbox ingestion into ClaimPilot events.
- Price-drop auto resolution.
- Damaged-item and return-window decision capture.
- Real Gmail order/status mail generation from the storefront.
- Optional carrier polling if a carrier adapter is configured.

## Demo Objective

By the end of this runbook you should have:

- A deployed frontend URL (CloudFront).
- A deployed backend URL (App Runner).
- Working Gmail OAuth credentials and token wired through Terraform runtime secrets.
- A deterministic demo sequence that can be presented in <=5 minutes.

## Prerequisites

### Local tools

1. AWS CLI installed and authenticated to your target account.
2. Terraform installed.
3. Docker installed and running.
4. Python 3.11+ installed (for optional token generation helper script).
5. Node.js 18+ installed (for frontend build).

### Accounts and access

1. AWS account with permission to manage App Runner, ECR, S3, CloudFront, IAM roles, and Secrets Manager.
2. Google account dedicated for the demo inbox (recommended).
3. Google Cloud project where Gmail API can be enabled.

### Project preparation

1. From repository root, copy the example vars file:

```bash
cp infra/aws/terraform.tfvars.example infra/aws/terraform.tfvars
```

1. Do not commit secrets to git. Keep tfvars local or managed via secure CI variables.

## AWS Demo Environment Setup

### 1. Create Gmail OAuth credentials and token

This project requires both:

- `gmail_credentials_json` (OAuth client JSON)
- `gmail_token_json` (authorized user token JSON)

#### 1.1 Create Google Cloud project and enable Gmail API

1. Open Google Cloud Console.
2. Create a new project for the demo.
3. Navigate to APIs and Services -> Library.
4. Enable Gmail API.

#### 1.2 Configure OAuth consent screen

1. Navigate to APIs and Services -> OAuth consent screen.
2. Select External user type (unless your org requires Internal).
3. Fill app name and support email.
4. Add test users (include your demo inbox Gmail address).
5. Add these scopes:

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`

#### 1.3 Create OAuth client JSON

1. Navigate to APIs and Services -> Credentials.
2. Click Create Credentials -> OAuth client ID.
3. Application type: Desktop app.
4. Download the JSON file.
5. This file content is your `gmail_credentials_json` value.

#### 1.4 Create authorized-user token JSON

Use a local one-time OAuth flow with the same scopes.

Install helper dependencies:

```bash
python -m pip install google-auth-oauthlib google-api-python-client
```

Run this script (adjust path to your downloaded client JSON):

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

scopes = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes)
creds = flow.run_local_server(port=0)

token_payload = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": creds.scopes,
}

print(json.dumps(token_payload))
```

Copy the printed JSON. That is your `gmail_token_json` value.

### 2. Configure runtime secrets in Terraform vars

Populate `infra/aws/terraform.tfvars`.

Recommended format for long JSON values is heredoc blocks to avoid manual escaping:

```hcl
runtime_secrets = {
  aws_access_key_id     = "..."
  aws_secret_access_key = "..."
  aws_session_token     = ""
  claimpilot_model_id   = "global.anthropic.claude-sonnet-4-6"

  gmail_credentials_json = <<GMAIL_CREDS
{"installed":{"client_id":"...","project_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"...","redirect_uris":["http://localhost"]}}
GMAIL_CREDS

  gmail_token_json = <<GMAIL_TOKEN
{"token":"...","refresh_token":"...","token_uri":"https://oauth2.googleapis.com/token","client_id":"...","client_secret":"...","scopes":["https://www.googleapis.com/auth/gmail.readonly","https://www.googleapis.com/auth/gmail.send"]}
GMAIL_TOKEN

  gmail_target_address = "your-demo-inbox@example.com"
  gmail_query          = "newer_than:14d (subject:(order OR shipped OR delivery OR receipt))"
}
```

### 3. Provision the AWS stack

Use this from repository root:

```bash
chmod +x scripts/deploy-demo.sh
./scripts/deploy-demo.sh
```

Or run Terraform directly:

```bash
terraform -chdir=infra/aws init
terraform -chdir=infra/aws plan
terraform -chdir=infra/aws apply
```

Capture the outputs from Terraform or the deploy script. You need:

- App Runner backend URL
- CloudFront frontend URL

### 4. Point the frontend at the deployed backend

Set the frontend API base to the App Runner URL before building or syncing the frontend:

```bash
export VITE_API_BASE=https://<your-app-runner-url>
```

If you are using the deployment script, Terraform will rebuild and republish the frontend bundle with the correct backend URL automatically.

The backend starts a Gmail watcher automatically on App Runner startup. Manual Gmail ingest is still available for backfill or debug, but it is no longer required for the normal demo flow.

The dashboard includes a `Run full demo flow` action that triggers `POST /demo/runbook` and executes the three deterministic beats in one step.

## Pre-Demo Setup

Use this checklist before recording or presenting.

1. Confirm deployed service health:

Run these checks against the deployed backend before you present:

```bash
curl -s https://<your-app-runner-url>/health
curl -s https://<your-app-runner-url>/health/gmail
```

1. Run smoke checks from repository root:

```bash
./scripts/smoke-aws-demo.sh
```

1. Confirm expected responses:

- `health` returns `status: ok` and `configured: true`.
- `health/gmail` returns `status: ok` when Gmail credentials are valid.

1. Open the CloudFront frontend URL and verify data loads.
1. Send a quick test order (via seed endpoint) and verify it appears in inbox.
1. Keep one terminal ready for fallback API commands during recording.

## Demo Data Creation

Use this sequence to keep the demo deterministic.

1. Seed storefront once:

### Option A: Use the storefront to create real Gmail mail

Seed the storefront demo through the deployed backend. This creates products and sends Gmail order/status messages to the configured inbox:

```bash
curl -X POST https://<your-app-runner-url>/storefront/seed-demo
```

1. Confirm it creates four products and sends order/status mail for:

- 4K Monitor
- Wireless Headphones
- Travel Backpack
- Desk Lamp

1. Wait one watcher cycle for automatic ingestion.
1. If needed, force backfill ingest once:

```bash
curl -X POST "https://<your-app-runner-url>/integrations/email/gmail/ingest?user_id=user-demo&max_results=10"
```

1. Optional carrier poll if configured:

```bash
curl -X POST https://<your-app-runner-url>/integrations/tracking/poll
```

### Manual actions (fallback path)

Use these only if you need to recover during the live demo.

Create a single order:

```bash
curl -X POST https://<your-app-runner-url>/storefront/orders/monitor
```

Trigger a price drop email for that order:

```bash
curl -X POST "https://<your-app-runner-url>/storefront/orders/SF-0001/price-drop?new_price=199"
```

Trigger a return-window email:

```bash
curl -X POST https://<your-app-runner-url>/storefront/orders/SF-0001/return
```

Trigger a damaged-item claim email:

```bash
curl -X POST "https://<your-app-runner-url>/storefront/orders/SF-0001/claim?claim_type=damaged_item"
```

## Timed End-to-End Demo Flow (<=5 minutes)

Use this exact pacing for a clean hackathon submission video.

### 00:00 - 00:30 Intro

Action:

1. Show CloudFront frontend URL open.
2. Show `/health` and `/health/gmail` responses in terminal.

Vocal script:

"ClaimPilot is a post-purchase agent that watches order signals, auto-resolves low-risk exceptions, and asks for user input only when judgment is required."

### 00:30 - 01:20 Seed real demo data

Action:

1. Trigger `POST /storefront/seed-demo`.
2. Show dashboard orders and activity feed updating.

Vocal script:

"This seed call creates realistic storefront activity and sends real Gmail order and status messages to the configured inbox."

### 01:20 - 02:10 Beat 1 Price drop auto-resolve

Action:

1. Trigger the price-drop scenario from UI or API.
2. Show audit entries for `exception_classified` and `auto_resolve`.

Vocal script:

"For low-risk cases like price drops, the agent resolves automatically and records the full decision path in the audit log."

### 02:10 - 03:15 Beat 2 Damaged item decision capture

Action:

1. Trigger damaged-item flow.
2. Open pending decision card.
3. Click Approve (or call decision API).
4. Show pending count drops.

Vocal script:

"For ambiguous issues like damage claims, ClaimPilot asks for a human decision and then completes the flow end-to-end."

### 03:15 - 04:10 Beat 3 Return-window decision capture

Action:

1. Trigger return-window flow.
2. Approve or reject from the dashboard.
3. Show `decision_captured` in audit trail.

Vocal script:

"Return-window decisions are time-sensitive and user-specific, so they stay human-in-the-loop with full traceability."

### 04:10 - 04:45 Reliability and deploy reproducibility

Action:

1. Show smoke script command and result summary.
2. Briefly show Terraform-driven deploy path.

Vocal script:

"The same repository contains deployment and smoke checks so judges can reproduce this environment on AWS with minimal manual setup."

### 04:45 - 05:00 Close

Action:

1. Show final audit timeline and pending decision count at zero.
2. End on architecture or README docs links.

Vocal script:

"ClaimPilot demonstrates a real Strands-powered agent doing practical post-purchase work, with safe automation boundaries and human escalation where needed."

## Quick Fallback API Commands During Recording

If the UI stalls, use these commands and continue the demo:

```bash
curl -X POST https://<your-app-runner-url>/storefront/seed-demo
curl -X POST "https://<your-app-runner-url>/integrations/email/gmail/ingest?user_id=user-demo&max_results=10"
curl -X POST https://<your-app-runner-url>/demo/runbook
```

## Troubleshooting

- If `/health` returns `STRANDS_NOT_CONFIGURED`, verify runtime secret injection and App Runner service revision.
- If `/health/gmail` fails, verify OAuth consent test user access and both required scopes.
- If inbox ingestion is empty, relax `gmail_query` temporarily (for example `newer_than:30d`).
- If token expires, regenerate `gmail_token_json` with the same client and scopes.
- If frontend appears stale, verify it points to the current backend URL and rerun deploy/sync.

## Cleanup

Tear down the AWS demo when you are done:

```bash
terraform -chdir=infra/aws destroy
```
