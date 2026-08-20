# Phase 0 Step 1: Rules Lock and Scope Freeze

This file is the execution artifact for Step 1.

## 1. Locked MVP Scope

In-scope demo beats:
- Beat A: Price drop auto-resolution.
- Beat B: Damaged-item claim with user photo decision.
- Beat C: Return-window closing decision and action.

In-scope platform constraints:
- Single-user MVP.
- One email ingestion path.
- One carrier tracking adapter.
- Mock storefront claim endpoint.

## 2. Explicit Non-Goals

- Multi-user account system.
- Multi-carrier orchestration.
- Full production-grade retail portal automation.
- Complex front-end polish beyond demo clarity.

## 3. Definition of Done

Technical DoD:
- Event pipeline executes for all three beats.
- Decision table routes correctly to auto-resolve or user decision.
- Audit log records every major transition.

Testing DoD:
- Unit and pipeline tests pass.
- Three E2E scenarios are reproducible.

Submission DoD:
- Required artifacts exist and are publicly accessible.

## 4. Acceptance Criteria

- Scenario A produces auto-resolve action without user prompt.
- Scenario B produces pending decision prompt and completes after user input.
- Scenario C produces a return decision prompt before deadline.
- No hardcoded secrets in repository.

## 5. Risks and Mitigations (Step-1 View)

- External API instability: keep deterministic fallback fixtures.
- Time overrun: freeze feature scope before adapter expansion.
- Demo fragility: prioritize reproducible scripts over live improvisation.
