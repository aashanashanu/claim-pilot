# Testing Strategy

## Objectives

- Prove classifier correctness.
- Prove event routing correctness.
- Prove end-to-end scenario reliability.
- Prove secure handling of secrets and sensitive fields.

## Test Layers

### Unit Tests

Scope:
- Parser behavior for known/unknown email formats.
- Decision table outcomes per exception type.
- Threshold rules for high-value and low-evidence scenarios.
- Idempotency key generation and duplicate-event handling.

Pass criteria:
- Deterministic outputs for fixed fixtures.

### Integration Tests

Scope:
- OrderDetected -> StatusChanged -> AutoResolve/NeedsDecision routing.
- Audit log entries for each transition.
- Adapter boundary mocks for mailbox/carrier/storefront APIs.
- Decision capture endpoint and dashboard-facing pending decision state.

Pass criteria:
- All expected events published once.
- Audit timeline matches expected state machine progression.
- Decision submissions update the audit log and pending count exactly once.

### End-to-End Demo Tests

Scenario A: Price drop auto-resolve
- Trigger price reduction.
- Expect automatic resolution event and audit success entry.

Scenario B: Damaged item decision
- Trigger damaged flag.
- Expect pending decision event.
- Submit photo decision payload.
- Expect completed claim action.

Scenario B2: Human decision capture
- Seed a pending decision from damaged-item or return-window flow.
- Approve or reject through the API/UI.
- Expect `decision_captured` audit entry and pending count to drop to zero.

Scenario C: Return-window closing
- Seed order near deadline.
- Expect decision prompt and path completion.

Pass criteria:
- All three scenarios complete without code edits or manual DB mutation.

### Reliability Tests

- Duplicate event replay does not produce duplicate irreversible actions.
- Transient external API failure follows retry policy.
- Dead-letter handling captures exhausted retries.

Pass criteria:
- No data corruption.
- Consistent final state after retries/replays.

### Security Tests

- No hardcoded secrets in source tree.
- Redacted logs for sensitive fields.
- Session token TTL and scope validation.

Pass criteria:
- Secrets only via environment/secret manager.
- Logs contain no credential material.

## Test Execution Commands

```bash
pytest
python -m claimpilot.demo_seed
pytest tests/test_phase2_integrations.py tests/test_phase3_decision_capture.py tests/test_storefront.py
```

Future commands (as adapters are added):

```bash
pytest -m integration
pytest -m e2e
```
