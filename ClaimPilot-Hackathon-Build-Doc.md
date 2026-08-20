# ClaimPilot — Hackathon Build Doc

*An Everyday Agent that watches your deliveries and purchases silently, resolves what it safely can, and only interrupts you for a real decision.*

---

## The Problem

- Porch piracy alone costs Americans an estimated **$37 billion a year**, with roughly **104 million packages stolen** — and **25% of victims never get reimbursed at all**, mostly because filing a claim across a dozen different retailer/carrier portals is more friction than the refund is worth.
- The same friction shows up everywhere else in the "after you hit buy" lifecycle: price drops within a retailer's adjustment window go unclaimed, return windows close unnoticed, damaged items sit un-disputed.
- Existing tools (price trackers, return-window reminders) are single-purpose and require the user to remember to open them. Nothing runs quietly across *all* of it and only speaks up when a human decision is actually needed.

**One-liner:** ClaimPilot watches every order you place, silently resolves the stuff that doesn't need you, and pings you — once, with a clear choice — only when it genuinely can't decide without you.

---

## End-to-End Workflow

1. **Detect** — a new order shows up (confirmation email arrives)
2. **Track** — agent watches the shipment in the background
3. **Classify** — something goes off-script: late, lost, damaged, price drop, return window closing
4. **Act or ask** — low-risk cases are resolved automatically; ambiguous, high-value, or judgment-call cases get a single-tap ping
5. **Close the loop** — refund/replacement confirmed, logged to an audit trail, done. The user only ever sees decision points and final outcomes — never the process.

---

## Connecting to Orders Without Ever Touching a Retailer Password

This is the part judges will push on — the answer is the agent almost never needs retailer credentials at all.

| Need | How it's done | Credentials involved |
|---|---|---|
| Discover a new order | Read-only Gmail/Outlook API scope, filtered to a "Purchases" label | None — just a revocable mail-read grant |
| Track a shipment | Call the carrier's own tracking API (UPS/FedEx/USPS) with the tracking number | None — tracking lookups are anonymous by design |
| Check for a price drop | Re-check the public product page price vs. price paid | None — public page |
| Submit a claim/return on a portal with no public API | Reuse a short-lived, scoped **session token** captured from a one-time user login, stored encrypted in a secrets vault (AWS Secrets Manager / KMS) | Session token only — never the raw password, never stored long-term, per-merchant scoped, expires, every action logged |

**Demo-safety note:** don't live-scrape a real retailer with real credentials in front of judges — brittle and legally gray. Build a small mock storefront for the "submit a claim" leg (fully real, fully yours to control) and use the *real* UPS/USPS tracking APIs for the tracking leg (genuinely public and stable). That gives a technically honest demo without the fragility of impersonating a login flow live.

---

## Claim & Refund Logic — What's Automatic vs. What Pings

| Exception | Agent action | When it pings |
|---|---|---|
| Price drop within adjustment window | Auto-files the refund request | Never — bundled into end-of-day "here's what I did" digest |
| Delayed past expected delivery | Auto-files a carrier trace/inquiry | Only if still stuck after N days with no resolution |
| Marked delivered, not received | Drafts the claim with available evidence (carrier delivery photo/geo) | Only if claim amount is above a $ threshold, or evidence is weak/contradictory |
| Item arrived damaged | Can't act without proof | Immediately — one tap opens the camera, user sends a photo, agent finishes the claim |
| Return window closing on an unused item | Doesn't act without the user — this is a real judgment call | Always, with a countdown. If no response by T‑minus‑1‑day, a safe default (initiate the return) kicks in rather than silently missing the window |

---

## Notification / Ping Design

- One push notification, one decision, two buttons. Never "open the app and figure it out."
- FYI-only outcomes (refund posted, claim filed successfully) are bundled into a single daily digest, not individual interrupts.
- Only genuinely time-sensitive or ambiguous cases interrupt immediately.
- Every ping states the decision plainly: *"$12 price-adjustment refund ready to file — send it?"* not a link to a dashboard.

---

## Suggested Architecture (AWS-native, weekend-buildable)

```
Gmail/Outlook webhook (order email arrives)
        │
        ▼
Lambda: parse order → extract order #, item, price, tracking #
        │
        ▼
EventBridge/SQS: "OrderDetected" event
        │
        ▼
Step Function (scheduled): poll carrier tracking API per active shipment
        │
        ▼
EventBridge: "StatusChanged" event
        │
        ▼
Exception-classifier service: applies the decision table above
        │
        ├──► "AutoResolve" event ──► Resolution worker
        │        (calls carrier claim API / price-adjust endpoint /
        │         mock-store claim API, using vaulted session token)
        │        → logs every action to a DynamoDB audit table
        │
        └──► "NeedsDecision" event ──► SNS/Twilio push notification
                 (single decision, two buttons)
```

Secrets vault: AWS Secrets Manager, KMS-encrypted, one secret per merchant per user, short TTL, only assumable by the resolution worker's IAM role.

This is the same event-driven shape as a Kafka pipeline — just AWS-native components for a weekend build.

---

## Demo Script (3 beats, ~2 minutes)

1. **Price drop** — trigger a price change on the mock store's product page. Within seconds, ClaimPilot detects it and auto-files the refund, silently. *(Shows: fully automatic, no human needed.)*
2. **Damaged item** — "report" a damaged item via a form. Phone buzzes immediately asking for a photo. Snap it on stage. Claim auto-completes right after. *(Shows: pings for exactly what's needed, nothing more.)*
3. **Return window closing** — pre-seed an order at day 27 of a 30-day window. Live push appears with a countdown and two buttons. Tap "Return." Agent kicks off the return. *(Shows: real judgment calls get a real decision, not a silent guess.)*

Each beat sits at a different point on the silent-to-decision spectrum — which is the whole pitch.

---

## MVP Scope (if time is short)

**Build first:**
- Email parsing → order detection (this is the credibility anchor — get it working on real inbox data if possible)
- Carrier tracking API polling (real UPS or USPS sandbox — pick one)
- The exception-classifier decision table (can be simple rules, doesn't need to be ML)
- The push/ping UI for one exception type (damaged item is the most visual)

**Cut if needed:**
- Multi-carrier support (one carrier is enough to prove the pattern)
- The mock storefront's full checkout flow (a static seed of 3-4 "orders" is fine)
- The daily digest batching (can be simulated/mocked for demo)

## Anticipated Judge Questions

- *"What stops this from just being a scraper with extra steps?"* — It isn't one: it never logs into a retailer as the user for tracking or price checks, only for the narrow claim-submission step, and even then only via a vaulted session token, not the password.
- *"What if the agent gets a refund decision wrong?"* — Every irreversible or high-value action has a dollar threshold and evidence-quality check baked into the decision table; anything below the bar for confidence pings instead of acting.
- *"How does this scale past one user's inbox?"* — The pipeline is already event-driven (EventBridge/SQS), so it's the same shape whether it's one user or one million; the only per-user cost is the scheduled tracking polls.

---

*Working name: ClaimPilot. Alternatives to consider: Doorstep, Recoup, ParcelPilot.*
