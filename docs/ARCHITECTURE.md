# ARCHITECTURE.md — Agentic Guard

## System diagram (text form — recreate visually for the pitch video)

```
User intent (NL or scripted)
        |
        v
[Agent Orchestrator] --(builds tool call)--> 
        |
        v
[Interceptor / Risk Manager] --(reads)--> [Mandate: Postgres/Supabase]
        |
   approved?  --no--> [blocked response to user] + [audit log entry]
        |
       yes
        v
[MCP / Payment Client] --(mock OR real Razorpay MCP)-->
        |
   success/failure (incl. simulated NPCI codes)
        |
        v
[Orchestrator maps result to user-facing response] + [audit log entry]
        |
        v
[Dashboard] <--(reads live)-- [Postgres: mandate + audit log tables]
```

## Why this shape, specifically

The Interceptor sits BETWEEN intent-formation and execution, not
alongside it and not after it. This is the one architectural decision
that matters most to the project's thesis. If asked "why not just have
the LLM check its own limits," the answer is: an LLM's judgment is
exactly what a prompt injection attacks. A rule-based gate that the
LLM cannot reason its way around is the point.

## Data flow ownership

- **Mandate** is the single source of truth for authority. It is never
  mutated by the Agent or Payment Client — only by the Interceptor's
  `revoke()` method or an explicit admin action.
- **Audit log** is append-only. Nothing in the system ever deletes or
  edits a log entry, including failed/blocked ones — the ledger's
  credibility depends on this.
- **Catalog** is read-only at runtime from the Agent/Interceptor's
  perspective.

## Swappable components

| Component | Mock (current) | Real (target) | Shared interface |
|---|---|---|---|
| Payment execution | `mcp_client/razorpay_mock.py` | `mcp_client/razorpay_real.py` (Razorpay MCP server, test mode) | `execute_payment(tool_call) -> PaymentResult` |
| Cart/intent parsing | Scripted SKU/qty tuples | Claude API tool-use call against the catalog | `build_cart(intent) -> tool_call dict` |
| Storage | Flat YAML/JSON/JSONL (prototype phase) | Postgres via Supabase | Same schema, different persistence layer |

Any AI coding tool working on this repo should preserve these
interfaces exactly when swapping an implementation — the Interceptor
and Orchestrator must never need to change when the backing
implementation changes.

## Failure handling philosophy

Two distinct failure categories exist and must be handled differently:

1. **Policy failures** (Interceptor blocks) — known, expected, deterministic.
   Always produce a specific code and a plain-language explanation.
   Never retried automatically.
2. **Network/execution failures** (payment layer fails after approval) —
   e.g. NPCI Z9/U30/U16. Handled per-code, never with a generic
   "something went wrong," and never with blind retry loops.

## Security boundaries (demo scope, but treat seriously)

- Test-mode credentials only, sourced from environment variables, never
  committed to the repo.
- The Interceptor must be the only code path with permission to call
  the Payment Client's execution function — enforce this at the module
  level (Payment Client functions should not be imported directly by
  the Agent Orchestrator; only the Interceptor's approved path calls
  through to it).
