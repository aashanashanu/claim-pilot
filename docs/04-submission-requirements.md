# Submission Requirements Checklist

This checklist maps the Agents for Humans hackathon requirements to concrete project artifacts.

## Current Status (2026-08-31)

Legend: Complete = present in repo, Open = still needs a submission artifact or verification.

| Rule item | Status | Evidence in repo | Fix needed |
| --- | --- | --- | --- |
| Uses Strands Agents SDK in real workflow | Complete | `src/claimpilot/agent_runtime.py`, `tests/test_strands_integration.py` | None |
| Public repo with all code/assets/instructions | Open | README and docs are complete, but public URL is not set in repo docs | Add final public repo link in Devpost submission |
| MIT or Apache license in root | Complete | `LICENSE` | Verify Devpost points to this repo |
| README included | Complete | `README.md` | None |
| Architecture diagram included | Complete | `docs/01-architecture-diagram.md` | None |
| End-to-end working demo instructions | Complete | `docs/08-end-to-end-demo-guide.md`, `scripts/smoke-aws-demo.sh` | None |
| Public video (<=5 min) with demo and pitch | Open | Demo playbook exists in `docs/06-demo-and-judging-playbook.md` | Record and upload final video, then add link to submission |
| Submission text description | Open | Draft narrative in `ClaimPilot-Hackathon-Build-Doc.md` | Copy polished version into Devpost description |
| AWS Builder ID in submission | Open | Not stored in repo by design | Add Builder ID in Devpost form |
| Project available for judging/testing period | Open | Deploy + smoke path exists (`scripts/deploy-demo.sh`, `scripts/smoke-aws-demo.sh`) | Keep live URL available through judging period |
| Third-party usage authorization | Open | Integrations documented (`src/claimpilot/integrations.py`) | Add final disclosure note in submission text |

## Required Items

- Project uses Strands Agents SDK in a real, non-trivial workflow.
- Public repository link with all source/assets and run instructions.
- Open-source license file (MIT or Apache) in repository root.
- README with setup, usage, architecture, and testing instructions.
- End-to-end demo guide for setup, pre-demo checks, data creation, and live flows.
- Architecture diagram included in repo.
- Public video (<=5 minutes) showing working end-to-end demo and pitch.
- Devpost text description explaining features and functionality.
- AWS Builder ID included in submission.

## Strongly Recommended

- Public live demo link for easier technical evaluation.
- Deterministic test path for judges.
- Optional builder.aws post for bonus points.

## Compliance Constraints

- New project created during submission period.
- Authorized use of all third-party APIs/services.
- No private or broken links in submission package.
- Project available for judge testing through judging period.

## Pre-Submit Gate

- Repo is public and links work from a signed-out browser.
- Video link is public and playable.
- README quick-start works from clean clone.
- End-to-end demo guide works from clean clone and covers the complete live flow.
- Diagram and testing instructions are discoverable in README.
- No secrets are committed.

## Last-mile Validation Commands

Run from repository root:

```bash
python -m pytest
cd frontend && npm run build && cd ..
./scripts/smoke-aws-demo.sh
```
