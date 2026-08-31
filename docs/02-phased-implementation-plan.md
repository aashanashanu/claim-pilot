# Phased Implementation Plan

## Goal

Build a compliant, demo-ready ClaimPilot MVP that performs real end-to-end work with Strands Agents and AWS primitives.

## Phase 0 - Rules Lock and Scope Freeze (Step 1)

- Create compliance checklist from official rules.
- Freeze MVP to 3 demo beats:
  - Price drop auto-resolution
  - Damaged item user-photo decision flow
  - Return-window closing decision flow
- Define exclusions:
  - Single user
  - Single email provider
  - Single carrier adapter
  - Mock storefront claim endpoint
- Publish Definition of Done and acceptance tests.

Exit criteria:
- Phase-0 checklist approved.
- Scope and non-goals documented.
- Demo beats and pass/fail criteria locked.

## Phase 1 - Core Architecture and Runtime

- Implement event bus, domain models, decision table, handlers.
- Add auditable action records.
- Create deterministic demo seed runner.

Exit criteria:
- Pipeline routes events to AutoResolve/NeedsDecision correctly.
- Tests pass for baseline classifier and routing.

## Phase 2 - Ingestion and Tracking

- Add Gmail ingestion adapter for real inbox messages.
- Add storefront mail generation so the demo can create its own Gmail order/status traffic.
- Parse and normalize order metadata.
- Add single-carrier tracking adapter.
- Emit status-change events with idempotency keys and dead-letter handling.

Exit criteria:
- New order detection, status transition flow, and retryable carrier failures are reproducible.

## Phase 3 - Resolution and Human Decisioning

- Implement auto-resolution worker.
- Implement notification worker and user decision capture path.
- Expose a capture API and dashboard controls for approve/reject.
- Enforce thresholds and evidence checks.

Exit criteria:
- All 3 demo beats execute through the decision branch and audit log.
- Decision capture updates state, pending counts, and audit history consistently.

## Phase 4 - Demo Surface

- Build minimal dashboard for storefront orders, pending decisions, and audit timeline.
- Add deterministic scenario triggers.
- Provide storefront controls for buy, price-drop, return, and claim demo actions.

Exit criteria:
- End-to-end demo flow runs on demand with no manual patching.

## Phase 5 - Hardening and Testing

- Expand unit, integration, and E2E test coverage.
- Add reliability and security checks.

Exit criteria:
- Pass reliability, idempotency, and secret-safety checks.

## Phase 6 - Submission Packaging

- Finalize README, architecture diagram, setup instructions.
- Prepare and publish <=5 minute demo video.
- Prepare Devpost copy and links.

Exit criteria:
- Submission artifacts complete and publicly accessible.

## Phase 7 - Final Gate and Submit

- Judge-mode dry run from scratch.
- Submit early with verified links and testability.

Exit criteria:
- Successful submission and checklist sign-off.
