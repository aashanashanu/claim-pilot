## Plan: ClaimPilot Hackathon Implementation

Build the five requested hackathon points as five separate implementation phases, with Phase 2 covering both email and carrier integrations. The plan keeps the current demo-friendly architecture, extends the existing event pipeline, and adds only the minimum integration, deployment, and hardening work needed for a credible end-to-end submission.

**Steps**
1. **Phase 1: Strands decision path and rationale surfacing** *depends on current core runtime*
   - Confirm the Strands-backed decision engine is the primary decision path for at least one end-to-end scenario, with strict runtime enforcement when Strands is not configured.
   - Extend the audit trail and demo surfaces so the decision source, reason, and metadata are visible in the UI/API.
   - Fail fast with clear startup and health diagnostics when Strands is not configured.
   - Add or tighten tests around the agent-routing path, malformed agent output, and strict error behavior when Strands is unavailable.

2. **Phase 2: Email ingestion + carrier tracking integration** *depends on Phase 1*
   - Add an email ingestion adapter that can receive messages from a chosen provider and convert them into ClaimPilot orders/events.
   - Add a carrier tracking adapter that can fetch or poll shipment status and emit status-change events into the existing event bus.
   - Keep the current parser and tracking protocols, but move provider-specific logic into dedicated integration modules.
   - Add config/secrets handling for provider credentials and choose whether the demo uses real APIs, sandbox APIs, or mocked fallback adapters.
   - Add integration tests for message parsing, dedupe/idempotency, tracking transitions, and failure/dead-letter paths.

3. **Phase 3: Human-in-the-loop decision capture** *depends on Phase 1 and Phase 2 event flow*
   - Wire the `NeedsDecision` path to a concrete capture flow so user approval/rejection becomes an explicit event and audit record.
   - Expose the capture flow through the API and demo UI so the user can complete the loop without touching internals.
   - Ensure the capture path updates state, audit history, and any visible dashboard indicators consistently.
   - Add tests for approve/reject branches and for invalid or duplicate decision submissions.

4. **Phase 4: Deployment configuration and demo packaging** *depends on Phase 1-3*
   - Finish the AWS deployment path so the backend, frontend, and required configuration can be deployed and exercised together.
   - Verify environment variables, secrets injection, frontend API base URL handling, and any required build or upload steps.
   - Add or update deployment scripts so a reviewer can reproduce the demo without manual environment guesswork.
   - Confirm the live demo path matches what the judging video shows.

5. **Phase 5: Observability, reliability, tests, and docs** *depends on the implemented feature set*
   - Add structured logging and clearer correlation around ingestion, decisioning, resolution, and user-capture events.
   - Tighten idempotency, retry, dead-letter, and error-path handling where integrations can fail.
   - Add or update test scripts so the repository includes a clear local validation path and a small set of focused integration checks.
   - Update README, architecture diagram, and deployment docs so they match the implemented behavior and the submission instructions.

**Relevant files**
- `src/claimpilot/agent_runtime.py` — Strands engine routing, fallback behavior, and decision parsing.
- `src/claimpilot/handlers.py` — Event wiring for `OrderDetected`, `StatusChanged`, `AutoResolve`, `NeedsDecision`, and `DecisionCaptured`.
- `src/claimpilot/ingestion.py` — Email parsing and email-to-order event conversion.
- `src/claimpilot/tracking.py` — Carrier polling logic and status-change emission.
- `src/claimpilot/workers.py` — Resolution, notification, and decision capture adapters.
- `src/claimpilot/demo_service.py` — API-facing demo snapshot and scenario triggering.
- `src/claimpilot/demo_surface.py` — Scenario flows and audit-visible demo behavior.
- `src/claimpilot/api.py` — HTTP endpoints for demo and integration exercises.
- `src/claimpilot/store.py` — Processed-event, tracking-state, audit, and dead-letter stores.
- `infra/aws/main.tf` — AWS deployment resources, secrets injection, App Runner, S3, and CloudFront.
- `infra/aws/variables.tf` — Deployment inputs and credentials/model configuration.
- `scripts/deploy-demo.sh` — One-command demo deployment script.
- `README.md` — Quick start, deployment instructions, and demo guidance.
- `docs/01-architecture-diagram.md` — Target-state architecture and phase mapping.
- `docs/07-aws-demo-deployment.md` — AWS deployment walkthrough.
- `docs/03-testing-strategy.md` — Test coverage expectations and validation approach.

**Verification**
1. Run the existing unit and integration test suite after each phase and confirm the new tests pass.
2. Validate the demo flow locally through the API and frontend, including one auto-resolve path and one human-decision path.
3. Validate the AWS deployment path with Terraform plan/apply and a smoke test of the deployed backend/frontend URLs.
4. Check that the README and deployment docs describe the final runtime behavior, prerequisites, and demo steps accurately.

**Decisions**
- Keep the current demo-friendly architecture and expand it rather than replacing it with a heavier production stack.
- Phase 2 will target Gmail API for email ingestion, a mocked carrier adapter first, and mocked adapters as the integration mode so the team can ship a production-shaped flow without depending on live carrier credentials.
- Favor a safe fallback path for local/demo runs so the project remains runnable without cloud credentials.
- Treat the public submission and live demo as first-class deliverables, not afterthoughts.

**Decisions from user input**
- Phase 2 email integration will target Gmail API first.
- Phase 2 carrier integration will use a mocked carrier adapter first.
- Phase 2 will use mocked adapters rather than live credentials for the first pass.
- AWS deployment is required for the submission, so the implementation plan should include a reliable cloud demo path in addition to local development.
