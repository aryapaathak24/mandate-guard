# Software Requirements Specification (SRS)
## Project: Agentic Guard — A Mandate-Bounded Risk Interceptor for Agentic Commerce

**Version:** 1.0
**Date:** August 27, 2026
**Format loosely follows IEEE 830 structure**
**Companion document:** PRD_Agentic_Guard.md

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for Agentic Guard, a demonstration system built for the Razorpay AI Buildathon (Track 1: AI Growth & Agentic Commerce). It is intended to guide implementation and to serve as a reference for judges or collaborators who want to understand system behavior precisely.

### 1.2 Scope
The system consists of six logical modules:
1. **Catalog** — agent-discoverable merchant/product data
2. **Mandate** — the spending authority contract
3. **Interceptor (Risk Manager)** — deterministic policy enforcement
4. **Agent Orchestrator** — ties intent to action
5. **MCP / Payment Client** — executes payments (mock or real Razorpay MCP)
6. **Dashboard** — live visualization and control (including revocation)

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Meaning |
|---|---|
| MCP | Model Context Protocol — the interface an LLM agent uses to call external tools (here, Razorpay's payment tools) |
| Mandate | A structured, machine-readable grant of bounded payment authority, conceptually modeled on UPI Circle / AP2 mandate design |
| Interceptor / Risk Manager | The deterministic (non-LLM) component that approves or blocks a payment tool call against the mandate |
| MCC | Merchant Category Code |
| NPCI | National Payments Corporation of India — issues standardized transaction response/error codes |
| UAP | Unified Agent Protocol — NPCI's proposed national standard for AI agent authorization over UPI |
| SKU | Stock Keeping Unit — unique product identifier |
| Tool call | A structured request an agent makes to execute an action (e.g., `create_payment_intent`) |

### 1.4 References
- Razorpay AI Buildathon: https://razorpay.com/buildathon/
- Razorpay MCP server (reference): github.com/razorpay/razorpay-mcp-server
- Public reporting on NPCI's UAP and UPI Circle delegation limits
- Agentic Commerce Protocol (ACP) spec repository (OpenAI/Stripe)
- Google's Agent Payments Protocol (AP2) public documentation

### 1.5 Overview
Section 2 describes the system at a high level. Section 3 specifies detailed functional requirements per module. Section 4 covers external interfaces. Section 5 covers non-functional requirements. Section 6 covers data schemas. Section 7 covers key use-case flows. Appendices list the simulated NPCI error codes and the mandate schema in full.

---

## 2. Overall Description

### 2.1 Product Perspective
Agentic Guard is a standalone demonstration system, not an extension of an existing product. It is designed to run locally (single machine, no cloud deployment required) so that judges can clone and run it directly. It optionally integrates with Razorpay's real MCP server in test mode; absent that, a functionally equivalent mock payment client is used, sharing the exact same interface so the interceptor logic is identical either way.

### 2.2 Product Functions (summary)
- Accept a purchase intent (from a scripted cart or, optionally, parsed from natural language).
- Validate the resulting payment tool call against an active mandate.
- Execute the payment only if validation passes.
- Handle both policy blocks and network-level payment failures gracefully, without unbounded retries.
- Log every attempt, decision, and reason to an append-only audit log.
- Display mandate status, session statistics, and the full audit ledger live.
- Allow instant revocation of the mandate via the dashboard.

### 2.3 User Characteristics
- **Primary evaluators (judges):** technically literate, reviewing many submissions quickly; assume no walkthrough beyond the README and video.
- **Demo operator (you):** technically capable, running the system live or recording a video of it running.

### 2.4 Constraints
- Must run without requiring production financial credentials.
- Must be inspectable — favor flat, human-readable files (YAML/JSON/JSONL) over opaque databases, so judges can open a file and see the state directly.
- Must not depend on services requiring paid API access beyond what's already available (Razorpay test mode is free to provision).

### 2.5 Assumptions and Dependencies
- Python 3.10+ available in the judge's/demo environment.
- No GPU or heavy ML dependency required — the interceptor is rule-based, not model-based, by design (this is a stated architectural choice, not a limitation).

---

## 3. Functional Requirements

### 3.1 Module: Catalog

| ID | Requirement |
|---|---|
| FR-CAT-1 | The system shall expose a product catalog as a structured JSON file containing, at minimum, SKU, name, price (INR), and category for each product. |
| FR-CAT-2 | The system shall expose an `llms.txt` file at the catalog root describing the catalog's purpose, location, and agent usage instructions, to demonstrate agent-readable discovery. |
| FR-CAT-3 | Each product shall belong to exactly one category, used downstream by the Interceptor for category-based scope checks. |

### 3.2 Module: Mandate

| ID | Requirement |
|---|---|
| FR-MAN-1 | The system shall store the active mandate as a structured, human-readable file (YAML) containing: mandate ID, user ID, creation timestamp, spending limits, scope rules, and status. |
| FR-MAN-2 | The mandate shall define a **per-transaction limit** (maximum INR per single payment). |
| FR-MAN-3 | The mandate shall define a **cumulative limit** (maximum INR across a rolling time window) and the window duration in hours. |
| FR-MAN-4 | The mandate shall define a **velocity limit** (maximum payment attempts per minute), to prevent retry floods. |
| FR-MAN-5 | The mandate shall define an **allow-list of merchants** the agent may transact with. |
| FR-MAN-6 | The mandate shall define an **allow-list of Merchant Category Codes (MCC)** and an explicit **deny-list of product categories**, checked independently (a product may match an allowed MCC but still be denied by category). |
| FR-MAN-7 | The mandate shall have a status field with at least two states: `active` and `revoked`. |
| FR-MAN-8 | When revoked, the mandate shall record a `revoked_at` timestamp. |
| FR-MAN-9 | The mandate file shall be re-read (not cached indefinitely) on each evaluation cycle, so a revocation takes effect on the next attempted transaction without requiring a process restart. |

### 3.3 Module: Interceptor (Risk Manager)

| ID | Requirement |
|---|---|
| FR-INT-1 | The Interceptor shall evaluate every payment tool call against the active mandate **before** any payment execution call is made. |
| FR-INT-2 | The Interceptor shall be implemented as deterministic rule-based logic, not as an LLM call, so that its decisions cannot be influenced by prompt injection targeting the agent. |
| FR-INT-3 | The Interceptor shall reject any tool call if the mandate status is not `active`, with a distinct reason code (e.g., `MANDATE_REVOKED`). |
| FR-INT-4 | The Interceptor shall reject any tool call whose target merchant is not in the mandate's merchant allow-list, with a distinct reason code. |
| FR-INT-5 | The Interceptor shall reject any tool call containing at least one item whose category is in the mandate's category deny-list, with a distinct reason code identifying the offending item and category. |
| FR-INT-6 | The Interceptor shall reject any tool call whose total amount exceeds the per-transaction limit, with a distinct reason code (mapped conceptually to NPCI code Z8). |
| FR-INT-7 | The Interceptor shall track cumulative approved spend within the configured rolling window and reject any tool call that would cause the cumulative total to exceed the cumulative limit. |
| FR-INT-8 | The Interceptor shall track the rate of attempts (approved or blocked) and reject any tool call once the velocity limit is exceeded within the trailing 60-second window (mapped conceptually to NPCI code U16). |
| FR-INT-9 | The Interceptor shall log every evaluated tool call — approved or blocked — to an append-only audit log, including timestamp, full tool call payload, decision, code, and reason. |
| FR-INT-10 | The Interceptor shall expose a `revoke()` operation that sets the mandate status to `revoked` and persists this change to the mandate file. |
| FR-INT-11 | An unrecognized SKU in a tool call shall be rejected with a distinct reason code (`UNKNOWN_SKU`) rather than silently ignored or approved. |

### 3.4 Module: Agent Orchestrator

| ID | Requirement |
|---|---|
| FR-AGT-1 | The Orchestrator shall accept a purchase intent (minimally: a list of SKU/quantity pairs) and construct a structured tool call (merchant, items, total amount). |
| FR-AGT-2 | The Orchestrator shall submit every constructed tool call to the Interceptor before attempting payment execution. |
| FR-AGT-3 | If the Interceptor rejects a tool call, the Orchestrator shall not proceed to payment execution, and shall produce a user-facing response that explains the block in plain language without exposing raw internal error text. |
| FR-AGT-4 | If the Interceptor approves a tool call, the Orchestrator shall submit it to the Payment Client for execution. |
| FR-AGT-5 | If payment execution fails, the Orchestrator shall map the failure code to a distinct, non-generic user-facing response (i.e., an insufficient-funds failure shall not produce the same message as a bank-downtime failure). |
| FR-AGT-6 | The Orchestrator shall not automatically retry a failed or blocked payment without a new, explicit triggering intent — no silent retry loops. |

### 3.5 Module: MCP / Payment Client

| ID | Requirement |
|---|---|
| FR-PAY-1 | The Payment Client shall expose a single execution function accepting an approved tool call and returning a structured result (success/failure, code, message, payment ID if successful). |
| FR-PAY-2 | The mock Payment Client shall simulate at least the following failure codes: `Z9` (insufficient funds), `U30` (bank system down), `U16` (security block), in addition to a success case. |
| FR-PAY-3 | The Payment Client interface shall be identical whether backed by the mock implementation or a real Razorpay MCP server call, so the Interceptor and Orchestrator require no changes when swapping implementations. |
| FR-PAY-4 (optional, stretch) | When real Razorpay integration is available, the Payment Client shall use test-mode (`rzp_test_`) credentials exclusively; production credentials shall never be used in this system. |

### 3.6 Module: Dashboard

| ID | Requirement |
|---|---|
| FR-DSH-1 | The Dashboard shall display the current mandate's status (active/revoked), ID, and all configured limits and scope rules. |
| FR-DSH-2 | The Dashboard shall display live session statistics: count of approved transactions, count of blocked transactions, and cumulative spend against the cumulative cap. |
| FR-DSH-3 | The Dashboard shall display a reverse-chronological audit ledger of every logged tool call, showing: approved/blocked status, item summary, amount, reason/code, and timestamp. |
| FR-DSH-4 | The Dashboard shall refresh its displayed state at a regular interval (polling or equivalent) without requiring a manual page reload. |
| FR-DSH-5 | The Dashboard shall provide a single, clearly labeled control ("Revoke Access") that immediately invokes the mandate revocation operation. |
| FR-DSH-6 | Once revoked, the Dashboard's revoke control shall become disabled and visibly reflect the revoked state. |
| FR-DSH-7 | The Dashboard shall be servable via a lightweight local process requiring no external hosting or paid infrastructure. |

---

## 4. External Interface Requirements

### 4.1 User Interfaces
- The Dashboard is a browser-based UI served locally (e.g., `http://localhost:8420`), viewable in any modern browser without additional plugins.

### 4.2 Software Interfaces
- **Mandate file:** YAML, read/write, human-editable.
- **Catalog file:** JSON, read-only at runtime.
- **Audit log:** JSON Lines (`.jsonl`), append-only.
- **Dashboard API:**
  - `GET /api/state` → returns current mandate, computed stats, and recent audit entries as JSON.
  - `POST /api/revoke` → triggers mandate revocation; returns confirmation JSON.

### 4.3 Communications Interfaces
- All communication in the demo system is local (localhost) HTTP; no external network calls are required except when the optional real Razorpay MCP integration is enabled, in which case standard HTTPS calls to Razorpay's test-mode endpoints apply.

---

## 5. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Reliability | The system shall never execute a payment call that bypasses the Interceptor, under any code path. |
| NFR-2 | Auditability | Every decision (approved or blocked) shall be logged; no evaluated tool call shall be silently dropped from the audit trail. |
| NFR-3 | Transparency | All policy rules (limits, scope) shall be expressed as external configuration (YAML), not hardcoded in application logic, so they are inspectable without reading source code. |
| NFR-4 | Determinism | The Interceptor's decisions shall not depend on any LLM call — given the same mandate and tool call, the decision shall be reproducible. |
| NFR-5 | Usability | A judge cloning the repository shall be able to reach a running demo (agent script + dashboard) in under 10 minutes following the README. |
| NFR-6 | Portability | The system shall run on a standard local machine with Python 3.10+ and no GPU requirement. |
| NFR-7 | Security (demo scope) | No production financial credentials shall be stored, logged, or transmitted by this system at any point. |
| NFR-8 | Performance | Interceptor evaluation of a single tool call shall complete in well under 100ms, since it involves no network or model calls. |

---

## 6. Data Requirements / Schemas

### 6.1 Mandate schema (YAML)
```yaml
mandate_id: string
user_id: string
created_at: ISO-8601 timestamp
limits:
  max_per_transaction: number (INR)
  max_cumulative: number (INR)
  cumulative_window_hours: number
  max_attempts_per_minute: number
scope:
  allowed_mcc: [string]
  allowed_merchants: [string]
  blocked_categories: [string]
status: "active" | "revoked" | "expired"
revoked_at: ISO-8601 timestamp | null
```

### 6.2 Catalog schema (JSON)
```json
{
  "merchant_id": "string",
  "merchant_name": "string",
  "mcc": "string",
  "products": [
    { "sku": "string", "name": "string", "price_inr": number, "category": "string" }
  ]
}
```

### 6.3 Tool call schema
```json
{
  "tool": "create_payment_intent",
  "args": {
    "merchant_id": "string",
    "items": [ { "sku": "string", "qty": number, "name": "string" } ],
    "amount_inr": number
  }
}
```

### 6.4 Audit log entry schema (JSON Lines, one object per line)
```json
{
  "timestamp": "ISO-8601 timestamp",
  "tool_call": { "...as above..." },
  "decision": {
    "approved": boolean,
    "code": "string (e.g. OK, Z8, Z9, U16, U30, SCOPE_CATEGORY, SCOPE_MERCHANT, MANDATE_REVOKED, UNKNOWN_SKU)",
    "reason": "human-readable string"
  }
}
```

---

## 7. Key Use-Case Flows

### 7.1 UC-1: Successful bounded purchase
1. User expresses intent ("order rice, dal, and oil").
2. Orchestrator builds a tool call within mandate limits.
3. Interceptor evaluates: merchant allowed, category allowed, amount within per-transaction and cumulative caps, velocity within limit → **approved**.
4. Payment Client executes → success.
5. Orchestrator confirms purchase to user.
6. Audit log and Dashboard reflect the approved transaction.

### 7.2 UC-2: Blocked mandate breach (scope violation)
1. A malicious instruction (simulating prompt injection) attempts to purchase a blocked-category item (e.g., a gift card).
2. Orchestrator builds the corresponding tool call.
3. Interceptor evaluates: category is in the deny-list → **blocked**, code `SCOPE_CATEGORY`.
4. Payment Client is never invoked.
5. Orchestrator returns a plain-language explanation to the user.
6. Audit log and Dashboard reflect the blocked attempt with reason.

### 7.3 UC-3: Blocked mandate breach (amount violation)
1. Intent would exceed the per-transaction or cumulative cap.
2. Interceptor evaluates: amount check fails → **blocked**, code `Z8`.
3. Same downstream handling as UC-2.

### 7.4 UC-4: Graceful network failure
1. A tool call passes Interceptor evaluation (approved).
2. Payment Client execution simulates a network-level failure (`Z9`, `U30`, or `U16`).
3. Orchestrator maps the specific code to a distinct, non-generic response and does not automatically retry.
4. Audit log records the approved-but-failed attempt with the failure code.

### 7.5 UC-5: Live revocation
1. User (or demo operator) clicks "Revoke Access" on the Dashboard.
2. Dashboard calls `POST /api/revoke`.
3. Interceptor's `revoke()` sets mandate status to `revoked` and persists it.
4. Any subsequent tool call, regardless of otherwise being within limits, is blocked with code `MANDATE_REVOKED`.
5. Dashboard reflects the revoked state and disables the control.

---

## 8. Appendix A: Simulated NPCI-Style Error Codes

| Code | Meaning | System Behavior |
|---|---|---|
| Z9 | Insufficient funds in remitter account | Payment fails after approval; agent proposes an alternative rather than retrying |
| U30 | Bank system down / debit failed | Payment fails after approval; agent backs off rather than retrying immediately |
| U16 | Transaction blocked for security reasons / velocity exceeded | Used both as a payment-execution failure and, conceptually, as the Interceptor's own velocity-limit block code |
| Z8 | Transaction frequency / limit exceeded | Used as the Interceptor's amount/cumulative-limit block code |
| SCOPE_CATEGORY | (system-internal, not an official NPCI code) | Interceptor block: item category is on the mandate's deny-list |
| SCOPE_MERCHANT | (system-internal) | Interceptor block: merchant not in the mandate's allow-list |
| MANDATE_REVOKED | (system-internal) | Interceptor block: mandate status is not active |
| UNKNOWN_SKU | (system-internal) | Interceptor block: referenced product not found in catalog |

---

## 9. Appendix B: Out-of-Scope Items for Future Iteration
- Real-time LLM-based natural language cart construction (currently deterministic/scripted for demo reliability).
- Multi-mandate support (multiple concurrent users/agents).
- Persistent database backend (flat files are intentional for inspectability, not a limitation to "fix" without reason).
- Full compliance with NPCI's actual (unpublished, in-development) UAP specification — this system models the *concepts* only.
