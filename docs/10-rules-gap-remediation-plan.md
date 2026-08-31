# Rules Gap Remediation Plan

This plan compares the current ClaimPilot repository to the Devpost Agents for Humans rules and defines the remaining fix work required before final submission.

## Scope of this audit

- Rules source: [Agents for Humans rules](https://agentsforhumans.devpost.com/rules)
- Audit date: 2026-08-31
- Code and docs reviewed: backend, frontend, infra, scripts, tests, and submission docs.

## What is already aligned

- Strands-based agent workflow is implemented and test-covered.
- Public-license requirement is satisfied by the root `LICENSE` file.
- README, architecture diagram, and end-to-end demo docs are present.
- AWS deployment is reproducible via Terraform and scripted deploy flow.
- Post-deploy smoke checks exist and validate health plus demo execution.

## Remaining gaps and fix plan

### Gap 1: Public video is not yet published

Why it matters:

- Rules require a public video (<=5 minutes) that demonstrates a working project and pitch.

Fix plan:

1. Record a <=5 minute demo using the sequence in `docs/06-demo-and-judging-playbook.md`.
2. Upload to YouTube or Vimeo as public.
3. Add the final URL to Devpost submission fields.

Definition of done:

- Public video URL opens signed-out and duration is <=5:00.

### Gap 2: Devpost submission metadata is not yet finalized

Why it matters:

- Rules require text description and AWS Builder ID in the submission form.

Fix plan:

1. Use `ClaimPilot-Hackathon-Build-Doc.md` as source text for the final Devpost description.
2. Add AWS Builder ID in the required Devpost field.
3. Add optional live demo link (CloudFront URL) to improve technical implementation scoring.

Definition of done:

- Devpost draft contains complete text description, Builder ID, and live demo link.

### Gap 3: Third-party API authorization disclosure is implicit, not explicit

Why it matters:

- Rules require authorized use of third-party SDKs/APIs and compliance with terms.

Fix plan:

1. Add a short disclosure block in Devpost description listing third-party services used:

   - Gmail API (gmail.readonly + gmail.send)
   - AWS Bedrock via Strands SDK
   - Any carrier adapter used in the demo

2. Confirm all credentials/tokens used in demo are owned by the team and revocable.

Definition of done:

- Submission text includes explicit third-party usage disclosure.

### Gap 4: Judge-period availability process is not explicitly documented

Why it matters:

- Rules require project access for judging/testing through the judging period.

Fix plan:

1. Keep AWS demo deployment active through judging end date.
2. Run `scripts/smoke-aws-demo.sh` before submission and before judging checkpoints.
3. Keep fallback testing path available in README (local run + tests) in case live demo is temporarily unavailable.

Definition of done:

- Live URL is reachable and smoke checks pass at submission time.

## Development gaps still worth closing

### Gap 5: No CI gate for test, frontend build, and docs-link integrity

Why it matters:

- The project is runnable locally, but there is no automated pull-request gate to prevent regressions in tests, build output, or documentation links.

Fix plan:

1. Add a GitHub Actions workflow that runs `python -m pytest` and `cd frontend && npm ci && npm run build` on push/PR.
2. Add markdown link checking for `README.md` and `docs/*.md`.
3. Add badge/status note in README after workflow is live.

Definition of done:

- Pull requests show green checks for backend tests, frontend build, and docs links.

### Gap 6: Observability is basic for a live judge session

Why it matters:

- During judging, fast triage matters. Current docs describe flow well, but there is no explicit operator playbook for log correlation IDs and common failure signatures.

Fix plan:

1. Add a short `docs/11-operations-runbook.md` with expected log patterns and first-response actions.
2. Include top five production failure checks (`/health`, `/health/gmail`, token validity, secret injection, App Runner revision).
3. Add a single command section for collecting recent App Runner logs.

Definition of done:

- A reviewer/operator can diagnose the top failure modes in under five minutes.

## Execution checklist (recommended order)

1. Deploy latest stack and run smoke checks.
2. Record and publish final demo video.
3. Finalize Devpost text and metadata.
4. Perform signed-out link verification for repo, video, and live demo.
5. Freeze submission package.

## Risk notes

- Terraform CLI and cloud credentials must be available in the final environment to validate live deploy.
- Gmail token expiration can break live demo; refresh token prior to recording and submission.
- Keep runtime secrets only in AWS Secrets Manager and never in repository files.
