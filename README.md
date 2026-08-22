# ClaimPilot

ClaimPilot is an everyday agent that watches post-purchase orders, auto-resolves safe exceptions, and asks for user input only when judgment is required.

This repository contains implementation code plus a full documentation package for all build phases and submission readiness.

## Current Implementation Status

- Event-driven in-memory pipeline (`OrderDetected`, `StatusChanged`, `AutoResolve`, `NeedsDecision`)
- Decision table for the three locked MVP beats
- Auditable action records across classify and resolve flows
- Real Strands-compatible decision engine with safe rule fallback
- Demo seed runner and focused integration tests
- Phase 0 rule lock and scope freeze captured in [docs/05-phase-0-step-1-scope-freeze.md](docs/05-phase-0-step-1-scope-freeze.md)

## Documentation Pack

- Architecture diagram: [docs/01-architecture-diagram.md](docs/01-architecture-diagram.md)
- Phased plan: [docs/02-phased-implementation-plan.md](docs/02-phased-implementation-plan.md)
- Testing strategy: [docs/03-testing-strategy.md](docs/03-testing-strategy.md)
- Submission checklist: [docs/04-submission-requirements.md](docs/04-submission-requirements.md)
- Phase 0 Step 1 artifact: [docs/05-phase-0-step-1-scope-freeze.md](docs/05-phase-0-step-1-scope-freeze.md)
- Demo and judging playbook: [docs/06-demo-and-judging-playbook.md](docs/06-demo-and-judging-playbook.md)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
python -m claimpilot.demo_seed
```

## Project Phases

- Phase 0: Rules lock and scope freeze
- Phase 1: Core runtime and decision table
- Phase 2: Ingestion and carrier tracking
- Phase 3: Resolution and decisioning workers
- Phase 4: Demo surface
- Phase 5: Testing and hardening
- Phase 6: Submission packaging
- Phase 7: Final gate and submit

## Notes

- Phase 0 scope lock is complete and documented.
- Phase 1 core runtime is in progress and includes a real Strands-compatible decision path.
- External integrations (Gmail, carrier API, production AWS credentials) remain for the next implementation stage.
