## Plan: ClaimPilot End-to-End Hackathon Build

Build a compliant, demo-ready ClaimPilot MVP that proves Strands Agents can do real end-to-end work: ingest order signals, classify post-purchase exceptions, auto-resolve safe cases, and request user decisions only when necessary. Prioritize judging criteria (Technical Implementation, Design, Impact, Creativity, Presentation) and hard submission requirements (public repo, license, architecture diagram, working video, testability).

**Steps**
1. Phase 0 - Rules Lock and Scope Freeze (2-3 hours)
2. Confirm hackathon constraints in a project checklist: Strands Agents usage, public repo, OSS license, README, architecture diagram, <=5 minute public video, Builder ID, test access.
3. Freeze MVP scope to three demo beats from the concept doc: price drop (auto), damaged item (needs photo), return window closing (user decision).
4. Define explicit exclusions to protect timeline: single carrier only, one email provider only, mock storefront for claim submission, no multi-user auth.
5. Create Definition of Done with acceptance criteria for each beat and submission artifact. *blocks all later phases*

6. Phase 1 - Architecture and Environment Setup (4-6 hours, depends on 1-5)
7. Set up AWS primitives for event-driven flow: compute for agent workers, event bus/queue, datastore for orders/audit, secret storage for scoped session tokens.
8. Initialize Strands Agents integration and verify one minimal working agent action in local/dev environment.
9. Establish project skeleton and environment management (secrets in env/secret manager, never in source).
10. Document architecture baseline and data contracts for core events: OrderDetected, StatusChanged, AutoResolve, NeedsDecision. *parallel with step 8 after infra skeleton exists*

11. Phase 2 - Ingestion and Tracking Backbone (8-10 hours, depends on 6-10)
12. Implement order ingestion from email source using read-only permissions; extract order id, item, paid price, merchant, carrier/tracking, purchase date.
13. Persist normalized orders and initial status snapshots for idempotent re-processing.
14. Implement shipment polling for one carrier and status-change detection; emit StatusChanged only when state transitions occur.
15. Add deterministic retry and dead-letter handling so temporary API failures do not break the pipeline.
16. Add observability basics: structured logs, correlation ids, action outcome states. *parallel with steps 12-14*

17. Phase 3 - Decisioning and Resolution Engine (8-10 hours, depends on 11-16)
18. Encode rules from concept doc into a transparent decision table:
19. Price drop within adjustment window -> AutoResolve.
20. Delivery delay beyond threshold -> AutoResolve first, escalate if unresolved.
21. Delivered-not-received -> NeedsDecision above value/risk threshold.
22. Damaged item -> NeedsDecision requesting photo proof.
23. Return window nearing close -> NeedsDecision with safe default fallback.
24. Implement auto-resolution worker that calls controlled endpoints (mock storefront, carrier inquiry) and writes full audit entries.
25. Implement decision-notification worker for single-action prompts and decision capture.
26. Add guardrails: dollar thresholds, evidence confidence checks, irreversible-action confirmation rules.

27. Phase 4 - Demo Surface and UX Flow (6-8 hours, depends on 18-26)
28. Build minimal operator/demo UI that shows active orders, pending decisions, and audit timeline.
29. Add scenario toggles for deterministic demo triggers for each beat (price drop, damage report, return countdown).
30. Ensure one-notification-one-decision language is explicit and consistent with product promise.
31. Verify mobile-readable and desktop-readable flow for demo reliability.

32. Phase 5 - Testing and Hardening (6-8 hours, depends on 27-31)
33. Unit tests for parsing, classifier rule outputs, threshold guards, and idempotency keys.
34. Integration tests for event chain: ingest -> classify -> auto-resolve/needs-decision -> audit log.
35. End-to-end scripted tests for the three demo beats with pass/fail checkpoints and expected audit artifacts.
36. Reliability tests: duplicate event replay, transient provider failure, timeout and retry behavior, empty/malformed email handling.
37. Security checks: secret leakage scan, least-privilege review, token TTL validation, sensitive-field redaction in logs.

38. Phase 6 - Submission Packaging (4-6 hours, depends on 33-37)
39. Prepare public repository requirements: open-source license, complete README, setup/run instructions, architecture diagram, acknowledgments/disclosures.
40. Record <=5 minute video with strict structure: problem, who, why, then three end-to-end beats showing real agent work.
41. Prepare Devpost text description and ensure links are public and functioning (repo, video, optional live demo).
42. Optional score boost: publish builder.aws post(s) on implementation journey and link them.

43. Phase 7 - Final Gate and Submission (2-3 hours, depends on 38-42)
44. Perform judge-mode dry run: clone-from-scratch setup, run instructions, verify demo reproducibility.
45. Execute final compliance checklist and submit at least 12 hours before deadline.
46. Archive release notes and known limitations for post-submission Q&A.

**Relevant files**
- `/Users/aashanashanu/Documents/projects/self/claim-pilot/ClaimPilot-Hackathon-Build-Doc.md` - source concept, decision-table intent, demo narrative, and MVP boundaries to preserve.
- `/memories/session/plan.md` - living implementation plan and scope control for this session.

**Verification**
1. Rule compliance check: all required submission artifacts exist and are publicly accessible.
2. Stage 1 viability check: clear evidence that Strands Agents is actively used for agent decisions/actions.
3. Automated tests: unit + integration suites pass for parser, classifier, and event handlers.
4. E2E rehearsal: run all three demo beats twice without manual patching.
5. Reliability gate: retries/idempotency verified under duplicate events and transient external failures.
6. Security gate: no secrets in repository; token handling and audit logging meet stated constraints.
7. Presentation gate: video stays within time limit and clearly demonstrates end-to-end functionality.

**Decisions**
- Included scope: single-user, single-carrier, one email provider, mock storefront claim path, full audit trail.
- Excluded scope: multi-user auth, multi-carrier orchestration, production-grade billing/tenancy, full retailer live scraping.
- Core architecture choice: event-driven AWS-native pipeline with Strands-driven decisioning and explicit human-in-the-loop boundaries.

**Further Considerations**
1. Track choice recommendation: submit under Everyday Agents because the user story is strongest there.
2. Risk recommendation: keep one entirely deterministic fallback demo path in case live API instability appears during recording.
3. Time recommendation: lock feature freeze at least 12 hours before submission to prioritize reliability and presentation quality.