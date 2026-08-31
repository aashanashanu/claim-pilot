# End-to-End Demo Guide

This guide is for the deployed AWS demo environment. It covers infrastructure setup, pre-demo checks, automatic inbox watching, demo data creation, and the live presentation flow for ClaimPilot.

## What This Demo Covers

- Gmail-backed order creation from the storefront demo.
- Real inbox ingestion into ClaimPilot events.
- Price-drop auto resolution.
- Damaged-item and return-window decision capture.
- Real Gmail order/status mail generation from the storefront.
- Optional carrier polling if a carrier adapter is configured.

## AWS Demo Environment Setup

### 1. Provision the stack

Use the deployment guide to create the App Runner, ECR, S3, and CloudFront resources:

```bash
chmod +x scripts/deploy-demo.sh
./scripts/deploy-demo.sh
```

Before the first apply, copy `infra/aws/terraform.tfvars.example` to `infra/aws/terraform.tfvars` and fill in the runtime secret JSON object.

Or run Terraform directly:

```bash
terraform -chdir=infra/aws init
terraform -chdir=infra/aws apply
```

Capture the outputs from Terraform or the deploy script. You need:

- App Runner backend URL
- CloudFront frontend URL
- AWS region

### 2. Configure runtime secrets

The deployed backend reads all runtime values from the Terraform-managed JSON secret. Populate the `runtime_secrets` object in `infra/aws/terraform.tfvars` with these fields:

```hcl
runtime_secrets = {
	aws_access_key_id      = "..."
	aws_secret_access_key  = "..."
	aws_session_token      = ""
	claimpilot_model_id    = "global.anthropic.claude-sonnet-4-6"
	gmail_credentials_json = "{... Gmail OAuth client JSON ...}"
	gmail_token_json       = "{... Gmail authorized-user token JSON ...}"
	gmail_target_address   = "your-demo-inbox@example.com"
	gmail_query            = "newer_than:14d (subject:(order OR shipped OR delivery OR receipt))"
}
```

If you are refreshing the token, re-authorize with both Gmail scopes used by the app:

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`

### 3. Point the frontend at the deployed backend

Set the frontend API base to the App Runner URL before building or syncing the frontend:

```bash
export VITE_API_BASE=https://<your-app-runner-url>
```

If you are using the deployment script, Terraform will rebuild and republish the frontend bundle with the correct backend URL automatically.

The backend starts a Gmail watcher automatically on App Runner startup. Manual Gmail ingest is still available for backfill or debug, but it is no longer required for the normal demo flow.

## Pre-Demo Setup

Run these checks against the deployed backend before you present:

```bash
curl -s https://<your-app-runner-url>/health
curl -s https://<your-app-runner-url>/health/gmail
```

Expected outcome:

- `health` returns `status: ok` and `configured: true`.
- `health/gmail` returns `status: ok` when Gmail credentials are valid.

Then open the CloudFront frontend URL and confirm the dashboard loads from the deployed backend.

## Demo Data Creation

### Option A: Use the storefront to create real Gmail mail

Seed the storefront demo through the deployed backend. This creates products and sends Gmail order/status messages to the configured inbox:

```bash
curl -X POST https://<your-app-runner-url>/storefront/seed-demo
```

This creates four products and sends real order/status mail for:

- 4K Monitor
- Wireless Headphones
- Travel Backpack
- Desk Lamp

### Option B: Create individual storefront actions by hand

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

### Option C: Pull Gmail inbox messages into ClaimPilot

After the storefront sends mail, the backend watcher should ingest the inbox automatically. Use this endpoint only if you want to force a backfill or debug a missed message:

```bash
curl -X POST "https://<your-app-runner-url>/integrations/email/gmail/ingest?user_id=user-demo&max_results=10"
```

This turns the mail into ClaimPilot order and status events.

### Optional carrier step

If a carrier adapter is configured in the deployed runtime, poll it after the orders exist:

```bash
curl -X POST https://<your-app-runner-url>/integrations/tracking/poll
```

## Live Demo Flow

### Beat 1: Price drop auto-resolve

1. Seed the storefront or create a single monitor order.
2. Ingest the Gmail inbox if you created the order manually.
3. Trigger the price-drop scenario from the deployed dashboard or storefront.
4. Show the audit trail and the auto-resolve record.

Expected result:

- The price-drop case resolves without human approval.
- The audit log shows `exception_classified` and `auto_resolve`.

### Beat 2: Damaged item decision capture

1. Create or seed a damaged-item order.
2. Ingest the Gmail inbox so ClaimPilot sees the event.
3. Open the storefront demo panel in the deployed dashboard.
4. Find the pending decision card for the damaged order.
5. Click `Approve` to submit `approve_photo`.

You can also use the API directly:

```bash
curl -X POST "https://<your-app-runner-url>/decisions/ORD-123?decision=approve_photo&reason=Photo%20is%20clear"
```

Expected result:

- The pending decision count drops to zero after capture.
- The audit log includes `decision_captured` with `approved` status.

### Beat 3: Return-window decision capture

1. Create or seed a return-window order.
2. Ingest the Gmail inbox.
3. Show the dashboard pending decision card or the storefront order table.
4. Choose whether to approve or reject the return.

API example:

```bash
curl -X POST "https://<your-app-runner-url>/decisions/ORD-456?decision=reject&reason=Need%20more%20time"
```

Expected result:

- The choice is recorded as a `decision_captured` audit entry.
- The dashboard updates without editing any code or store files.

## Suggested Demo Script Order

1. Show the cloud-hosted frontend and confirm the backend health endpoints are green.
2. Seed the storefront and show that real Gmail messages were sent.
3. Ingest Gmail and show the new orders in the dashboard.
4. Trigger the price-drop flow and show auto-resolution.
5. Trigger the damaged-item flow and approve the pending decision.
6. Trigger the return-window flow and reject or approve it live.
7. Show the final audit trail and pending-decision count at zero.

## Troubleshooting

- If `/health` returns `STRANDS_NOT_CONFIGURED`, check the App Runner environment and Secrets Manager injection.
- If `/health/gmail` is not `ok`, re-check the Gmail credentials, token path, and scopes.
- If the storefront has no pending decisions, run Gmail ingest again after seeding the demo mail.
- If the frontend does not load data, verify `VITE_API_BASE` points at the App Runner URL before building or syncing the site.

## Cleanup

Tear down the AWS demo when you are done:

```bash
terraform -chdir=infra/aws destroy
```