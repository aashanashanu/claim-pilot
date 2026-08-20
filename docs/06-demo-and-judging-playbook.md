# Demo and Judging Playbook

## Video Structure (<=5 min)

1. Problem (30-45s)
- Post-purchase claim friction and missed reimbursements.
- Why users need silent automation with selective interruption.

2. Demo Beat A: Price Drop (60-75s)
- Trigger price drop.
- Show auto-resolution and audit entry.

3. Demo Beat B: Damaged Item (60-75s)
- Trigger damage event.
- Show user decision request and claim completion.

4. Demo Beat C: Return Window (60-75s)
- Show countdown prompt near deadline.
- Show decision and action path.

5. Close (30-45s)
- Recap value proposition and safety model.
- Mention Strands Agents role and extensibility.

## Judge-Mode Dry Run

- Clone from public repo in clean environment.
- Follow README quick start exactly.
- Run tests and demo seed path.
- Validate architecture doc and submission links.

## Talking Points for Likely Judge Questions

- Why not scrape retailer passwords?
  - Read-only inbox + tracking APIs + scoped short-lived session tokens.
- How do you prevent wrong autonomous actions?
  - Thresholds, evidence checks, and human-in-the-loop boundaries.
- What proves this is not smoke-and-mirrors?
  - Deterministic scenarios, tests, and auditable action history.
