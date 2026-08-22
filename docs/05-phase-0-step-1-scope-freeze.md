# Phase 0 Step 1: Rules Lock and Scope Freeze

This file is the execution artifact for Phase 0 tasks 1-4.

## 1. Hackathon Constraint Checklist

Check each item before moving into Phase 1 implementation.

- [ ] Use Strands Agents SDK in the core agent workflow.
- [ ] Public GitHub repo is created and kept public during judging.
- [ ] MIT or Apache-2.0 open-source license is present and visible.
- [ ] README includes setup instructions, project purpose, and run steps.
- [ ] Architecture diagram is present in the repo and readable.
- [ ] Public video is under 5 minutes and demonstrates the working project.
- [ ] AWS Builder ID is linked or recorded for the submission.
- [ ] Test access / run instructions are clear enough for judges to evaluate.
- [ ] Project uses one-user, one-carrier, single-provider MVP constraints.
- [ ] No secrets or credentials are committed to source control.

## 2. Locked MVP Scope

In-scope demo beats:
- Beat A: Price drop auto-resolution.
- Beat B: Damaged-item claim with user photo decision.
- Beat C: Return-window closing decision and action.

In-scope platform constraints:
- Single-user MVP.
- One email ingestion path.
- One carrier tracking adapter.
- Mock storefront claim endpoint.
- Event-driven core with auditable state transitions.

## 3. Explicit Non-Goals

- Multi-user account system.
- Multi-carrier orchestration.
- Full production-grade retail portal automation.
- Complex front-end polish beyond demo clarity.
- Multiple email providers or warehouse integrations.
- Real financial settlement, billing, or legal claims processing.

## 4. Definition of Done

Technical DoD:
- Event pipeline executes for all three beats.
- Decision table routes correctly to auto-resolve or user decision.
- Audit log records every major transition.
- Strands decision path is present and safe even if model credentials are absent.

Testing DoD:
- Unit and pipeline tests pass.
- Three end-to-end scenarios are reproducible.
- Duplicate/replay behavior is handling idempotent events safely.

Submission DoD:
- Required artifacts exist and are publicly accessible.
- README, license, architecture diagram, and run instructions are in place.
- No hardcoded secrets are stored in the repository.

## 5. Acceptance Criteria

- Scenario A produces auto-resolve action without user prompt.
- Scenario B produces pending decision prompt and completes after user input.
- Scenario C produces a return decision prompt before deadline.
- No hardcoded secrets in repository.
- The core workflow remains stable when cloud credentials are unavailable.

## 6. Risks and Mitigations (Phase 0 View)

- External API instability: keep deterministic fallback fixtures.
- Time overrun: freeze feature scope before adapter expansion.
- Demo fragility: prioritize reproducible scripts over live improvisation.
- AWS setup drift: keep the local default path working without credentials.
