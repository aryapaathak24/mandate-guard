# Agentic Guard

> **Agentic commerce isn't a checkout problem — it's an authorization problem.**

**Agentic Guard** is an AI shopping agent that completes purchases through a Razorpay-style payment flow, but every payment decision passes through a deterministic Risk Manager before any money moves. The interceptor is not an LLM — it's a rule-based gate that a prompt injection cannot talk its way around, enforcing a spending mandate (per-transaction limits, category restrictions, velocity limits, instant revocation) independently of the agent's own judgment.

Built for the **Razorpay AI Buildathon 2026 — Track 1: AI Growth & Agentic Commerce**.

---

## Why this exists

Letting an AI agent shop is the easy part. The hard, currently-unsolved part — the one NPCI's Unified Agent Protocol, Google's AP2, and Razorpay's own UPI Reserve Pay infrastructure are all being built to address — is letting that agent move real money without trusting its judgment completely. This project demonstrates one concrete architecture for that: **agents propose, a deterministic layer disposes**.

---

## Architecture

```text
User intent
    │
    ▼
Agent Orchestrator ──(builds a payment tool call)──▶
    │
    ▼
Risk Manager / Interceptor ──(validates against the mandate)──▶
    │
    ├── approved? ──no──▶ Blocked, logged, explained in plain language
    │
    └── yes
        ▼
Payment Client (mock now, real Razorpay MCP-compatible interface)
    │
    ▼
Result mapped to a distinct, honest user-facing response
    │
    ▼
Live Dashboard — mandate status, audit ledger, one-click revoke
```

Full technical detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## What's implemented

| Module | Status | Requirements covered |
| :--- | :---: | :--- |
| **Catalog** (agent-readable products + `llms.txt`) | ✅ | `FR-CAT-1` to `FR-CAT-3` |
| **Mandate** (spending authority contract) | ✅ | `FR-MAN-1` to `FR-MAN-9` |
| **Risk Manager / Interceptor** | ✅ | `FR-INT-1` to `FR-INT-11` |
| **Mock payment client** (simulated NPCI failure codes) | ✅ | `FR-PAY-1`, `FR-PAY-2` |
| **Agent Orchestrator** | ✅ | `FR-AGT-1` to `FR-AGT-6` |
| **Live dashboard** (mandate seal, audit ledger, revoke) | ⏳ in progress | `FR-DSH-1` to `FR-DSH-7` |
| **Real Razorpay MCP integration** | ⏳ pending test keys | `FR-PAY-3`, `FR-PAY-4` |

Every requirement above has a corresponding pytest test (see [`backend/tests/`](backend/tests/), named `test_<FR-ID>_<description>`), traceable to [docs/SRS.md](docs/SRS.md).

---

## Design decisions worth knowing about

- **The Interceptor never calls an LLM.** This is deliberate — see [`AGENTS.md`](AGENTS.md)'s "non-negotiable architectural rule." If it reasoned about requests instead of checking fixed rules, it could be reasoned with.
- **Policy is config, not code.** Spending limits and scope rules live in `backend/mandate/mandate.yaml`, not hardcoded in application logic — inspectable without reading source.
- **Every evaluated call is logged, approved or blocked.** The audit trail has no silent paths — that's what makes the ledger trustworthy.
- **Mock and real payment clients share one interface.** Swapping in real Razorpay test-mode credentials requires no changes to the Interceptor or Orchestrator.

---

## Running it locally

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Run test suite
pytest -v

# 3. Start the backend server
uvicorn main:app --reload
```
*Health check available at `http://localhost:8000/health`.*

---

## Documentation

- [docs/PRD.md](docs/PRD.md) — Product requirements, goals, personas, risks
- [docs/SRS.md](docs/SRS.md) — Full functional/non-functional spec, numbered FR-IDs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design and swappable components
- [AGENTS.md](AGENTS.md) — Context file for AI coding agents working in this repo

---

## Status

Actively being built for submission. See the "What's implemented" table above for current progress.
