# ClaimPilot Architecture Diagram

This diagram represents the full target architecture across all implementation phases, with a clear MVP path and future-ready extensions.

## System Diagram (Strands Explicit)

```mermaid
flowchart TD
    A[Order Email: Gmail/Outlook Webhook] --> B[Ingestion Worker]
    B --> C[Order Parser]
    C --> D[(Order Store)]
    C --> E[OrderDetected Event]

    E --> F[Tracking Orchestrator]
    F --> G[Carrier Tracking Adapter]
    G --> H[StatusChanged Event]

    H --> I[Decision Worker]
    I --> J[Strands Agent]
    J --> K{Policy Guardrails\nThresholds + Evidence Checks}

    K -->|Safe, low-risk| L[AutoResolve Event]
    K -->|Ambiguous/high-risk| M[NeedsDecision Event]

    L --> N[Resolution Worker]
    N --> O[Merchant Claim Adapter]
    N --> P[Carrier Inquiry Adapter]
    N --> Q[(Audit Log)]

    M --> R[Notification Worker]
    R --> S[Mobile/Web Decision UI]
    S --> T[UserDecision Event]
    T --> N

    J -.tool call.-> O
    J -.tool call.-> P
    J -.tool call.-> R

    U[(Secrets Manager + KMS)] --> N
    U --> O

    V[Observability: Logs/Metrics/Traces] --> B
    V --> F
    V --> I
    V --> J
    V --> N
    V --> R
```

## How Strands Works in This Flow

```mermaid
sequenceDiagram
    participant EV as EventBus
    participant DW as Decision Worker
    participant SA as Strands Agent
    participant PG as Guardrails
    participant RW as Resolution Worker
    participant NW as Notification Worker
    participant UI as User UI

    EV->>DW: StatusChanged(order context)
    DW->>SA: Decide(action, reason, metadata)
    SA-->>DW: Proposed action
    DW->>PG: Validate thresholds and evidence

    alt Action = auto_resolve
        PG-->>RW: AutoResolve event
        RW-->>EV: Action completed + audit entry
    else Action = needs_decision
        PG-->>NW: NeedsDecision event
        NW->>UI: One prompt, one decision
        UI-->>EV: UserDecision event
        EV->>RW: Continue resolution
    end
```

## Strands Responsibilities

- Convert status-change context into a structured decision: auto_resolve or needs_decision.
- Provide explainable rationale and metadata for audit logs.
- Select the next operational tool path (claim action, carrier inquiry, or notification).
- Defer high-risk or ambiguous cases to human confirmation.

## What Strands Does Not Replace

- Event transport and orchestration (EventBridge/SQS/Lambda pattern).
- Data storage (order and audit stores).
- Secret management (Secrets Manager + KMS).
- Policy enforcement guardrails (thresholds and evidence checks remain deterministic).

## Runtime Boundaries

- Ingestion boundary: read-only mailbox permissions; no retailer password collection.
- Decision boundary: Strands proposes actions, and guardrails enforce policy-safe automation.
- Security boundary: merchant session tokens are scoped, short-lived, and encrypted.
- Human-in-the-loop boundary: damaged-item proof and high-risk claims require explicit user decisions.

## Phase Mapping

- Phase 1: In-memory pipeline, classifier, audit base.
- Phase 2: Email ingestion and carrier tracking adapters.
- Phase 3: Resolution and decision workers with guardrails.
- Phase 4: Demo UI and scenario triggers.
- Phase 5: Reliability, security, and test hardening.
- Phase 6-7: Submission packaging and final compliance run.
