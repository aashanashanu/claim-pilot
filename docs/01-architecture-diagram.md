# ClaimPilot Architecture Diagram

This diagram represents the full target architecture across all implementation phases, with a clear MVP path and future-ready extensions.

## System Diagram

```mermaid
flowchart TD
    A[Order Email: Gmail/Outlook Webhook] --> B[Ingestion Worker]
    B --> C[Order Parser]
    C --> D[(Order Store)]
    C --> E[OrderDetected Event]

    E --> F[Tracking Orchestrator]
    F --> G[Carrier Tracking Adapter]
    G --> H[StatusChanged Event]

    H --> I[Exception Classifier]
    I --> J{Decision Table}

    J -->|Safe, low-risk| K[AutoResolve Event]
    J -->|Ambiguous/high-risk| L[NeedsDecision Event]

    K --> M[Resolution Worker]
    M --> N[Merchant Claim Adapter]
    M --> O[Carrier Inquiry Adapter]
    M --> P[(Audit Log)]

    L --> Q[Notification Worker]
    Q --> R[Mobile/Web Decision UI]
    R --> S[UserDecision Event]
    S --> M

    T[(Secrets Manager + KMS)] --> M
    T --> N

    U[Observability: Logs/Metrics/Traces] --> B
    U --> F
    U --> I
    U --> M
    U --> Q
```

## Runtime Boundaries

- Ingestion boundary: read-only mailbox permissions; no retailer password collection.
- Decision boundary: classifier only auto-resolves policy-safe actions.
- Security boundary: merchant session tokens are scoped, short-lived, and encrypted.
- Human-in-the-loop boundary: damaged-item proof and high-risk claims require explicit user decisions.

## Phase Mapping

- Phase 1: In-memory pipeline, classifier, audit base.
- Phase 2: Email ingestion and carrier tracking adapters.
- Phase 3: Resolution and decision workers with guardrails.
- Phase 4: Demo UI and scenario triggers.
- Phase 5: Reliability, security, and test hardening.
- Phase 6-7: Submission packaging and final compliance run.
