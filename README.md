<p align="center">
  <img src="https://img.shields.io/badge/Razorpay_AI_Buildathon-2026-1652F0?style=for-the-badge" alt="Razorpay AI Buildathon 2026" />
  <img src="https://img.shields.io/badge/Track_1-Agentic_Commerce-00C853?style=for-the-badge" alt="Track 1: Agentic Commerce" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
</p>

# 🛡️ Agentic Guard

### Mandate-Bounded Risk Interceptor for AI Commerce

> **Agentic commerce isn't a checkout problem — it's an authorization problem.**

An AI agent that can browse a product catalog and initiate UPI-style payments through Razorpay — but **every payment decision passes through a deterministic Risk Manager** before any money moves. The Interceptor is *not* an LLM; it's a rule-based gate that a prompt injection cannot talk its way around.

---

## 📌 The Problem

LLMs are great at understanding purchase intent and building shopping carts. But giving an AI agent a payment API key and trusting its judgment is a recipe for disaster — hallucinations, prompt injections, and social-engineering attacks can all bypass an LLM's "sense of responsibility."

**The industry knows this.** NPCI's Unified Agent Protocol, Google's AP2, and Razorpay's own Reserve Pay infrastructure are all being designed to solve this exact gap. Agentic Guard demonstrates one concrete, working architecture for it today:

> **Agents propose. A deterministic layer disposes.**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTENT                                │
│                     "Buy 2kg rice and dal"                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Agent Orchestrator   │ ← Builds a payment tool_call
              │   (deterministic /     │   from the product catalog
              │    LLM-powered)        │
              └────────────┬───────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   🛡️  Risk Manager / Interceptor     │ ← Pure rules, ZERO LLM calls
        │                                      │
        │   ✓ Mandate active?                  │
        │   ✓ Merchant on allow-list?          │
        │   ✓ Category not blocked?            │
        │   ✓ SKU exists in catalog?           │
        │   ✓ Amount ≤ per-txn limit?          │
        │   ✓ Cumulative spend within cap?     │
        │   ✓ Velocity ≤ N attempts/min?       │
        └──────────┬────────────┬──────────────┘
                   │            │
            APPROVED       BLOCKED
                   │            │
                   ▼            ▼
        ┌─────────────┐  ┌──────────────────┐
        │  Payment     │  │ Rejected with    │
        │  Client      │  │ specific code    │
        │  (Mock/Real) │  │ (Z8, U16, etc.)  │
        └──────┬──────┘  └──────────────────┘
               │
               ▼
     ┌───────────────────┐         ┌────────────────────────────┐
     │  Success / NPCI   │────────▶│   📊 Live Dashboard        │
     │  failure code     │         │   • Mandate seal & status  │
     │  (Z9, U30, U16)  │         │   • Audit ledger (full)    │
     └───────────────────┘         │   • One-click revoke 🔴    │
                                   │   • Spend analytics        │
                                   └────────────────────────────┘

  Every path — approved, blocked, failed — writes to an append-only audit log.
```

Full technical detail → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## ✅ What's Implemented

| Module | Status | FR-IDs | Description |
|:-------|:------:|:-------|:------------|
| **Product Catalog** | ✅ Done | `FR-CAT-1` → `FR-CAT-3` | Agent-readable products with `llms.txt`, prices in INR, category tags |
| **Spending Mandate** | ✅ Done | `FR-MAN-1` → `FR-MAN-9` | YAML-based authority contract: per-txn limits, cumulative caps, scope rules |
| **Risk Manager / Interceptor** | ✅ Done | `FR-INT-1` → `FR-INT-11` | Deterministic policy engine — 7 sequential checks, distinct rejection codes |
| **Mock Payment Client** | ✅ Done | `FR-PAY-1`, `FR-PAY-2` | Simulates Razorpay MCP with NPCI failure codes (Z9, U30, U16) |
| **Agent Orchestrator** | ✅ Done | `FR-AGT-1` → `FR-AGT-6` | Cart builder → Interceptor → payment → plain-language user response |
| **Live Dashboard** | ✅ Done | `FR-DSH-1` → `FR-DSH-7` | Next.js + Tailwind: mandate seal, audit ledger, emergency revoke, spend stats |
| **Test Suite** | ✅ 15 files | — | Every FR-ID has a corresponding pytest, named `test_<FR-ID>_<description>` |

---

## 🔐 Core Design Decisions

| Decision | Rationale |
|:---------|:----------|
| **Interceptor never calls an LLM** | If it *reasoned* about requests, it could be *reasoned with*. Rule-based gates are immune to prompt injection. |
| **Policy is config, not code** | Spending limits live in [`mandate.yaml`](backend/mandate/mandate.yaml) — inspectable and editable without touching source. |
| **Every call is logged — no exceptions** | Approved, blocked, failed — every evaluation writes to the append-only audit ledger. No silent paths. |
| **Mock ↔ Real clients share one interface** | `execute_payment(tool_call) → PaymentResult`. Swapping implementations requires zero changes to the Interceptor or Orchestrator. |
| **No automatic retries** | A failed payment is surfaced to the user with a specific reason; the agent never silently retries (FR-AGT-6). |

---

## 🔎 Interceptor Rejection Codes

The Interceptor produces specific, machine-readable codes on every block — never a generic "denied":

| Code | Trigger | SRS Reference |
|:-----|:--------|:--------------|
| `MANDATE_REVOKED` | Mandate status ≠ active | FR-INT-3 |
| `SCOPE_MERCHANT` | Merchant not on allow-list | FR-INT-4 |
| `SCOPE_CATEGORY` | Item in a blocked category (e.g. Gift Cards, Alcohol) | FR-INT-5 |
| `UNKNOWN_SKU` | SKU not found in the product catalog | FR-INT-11 |
| `Z8` | Amount exceeds per-txn limit *or* cumulative cap | FR-INT-6, FR-INT-7 |
| `U16` | Velocity exceeds N attempts/minute | FR-INT-8 |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ & npm

### Backend

```bash
cd backend
pip install -r requirements.txt

# Run the full test suite (15 test files, every FR-ID covered)
pytest -v

# Start the API server
uvicorn main:app --reload
# → http://localhost:8000/health
```

### Frontend (Dashboard)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Try It Out

1. **Start both servers** (backend on `:8000`, frontend on `:3000`)
2. **Open the dashboard** at `http://localhost:3000`
3. **Browse the catalog** — products, prices, and categories are live
4. **Attempt a purchase** — use the built-in demo presets:
   - ✅ **Normal purchase** — approved, payment ID returned
   - 🚫 **Over-limit** — blocked with `Z8`
   - 🚫 **Blocked category** — blocked with `SCOPE_CATEGORY`
   - 🚫 **Velocity flood** — blocked with `U16`
5. **Hit "Revoke Access"** — the mandate flips to `revoked`, all subsequent attempts are instantly blocked with `MANDATE_REVOKED`
6. **Check the audit ledger** — every decision is logged with timestamp, tool call payload, and outcome

---

## 📁 Project Structure

```
razorpay.win/
│
├── backend/
│   ├── main.py                     # FastAPI entrypoint, CORS, routes
│   ├── requirements.txt            # fastapi, uvicorn, pyyaml, pytest
│   │
│   ├── catalog/                    # Product catalog (FR-CAT)
│   │   ├── catalog.py              #   Loader
│   │   ├── products.json           #   Product data (SKU, price, category)
│   │   └── llms.txt                #   Agent-readable product descriptions
│   │
│   ├── mandate/                    # Spending mandate (FR-MAN)
│   │   ├── mandate.py              #   Load / save / revoke
│   │   └── mandate.yaml            #   The mandate contract (config-driven)
│   │
│   ├── interceptor/                # Risk Manager (FR-INT) ← THE CORE
│   │   └── risk_manager.py         #   7 deterministic checks, audit logging
│   │
│   ├── agent/                      # Orchestrator (FR-AGT)
│   │   └── orchestrator.py         #   Cart builder + payment execution
│   │
│   ├── mcp_client/                 # Payment client (FR-PAY)
│   │   └── razorpay_mock.py        #   Simulates Razorpay MCP + NPCI codes
│   │
│   └── tests/                      # pytest suite — 15 test files
│       ├── test_FR_INT_1_and_2.py   #   ... one per FR-ID
│       ├── test_FR_INT_3.py
│       └── ...
│
├── frontend/                       # Next.js 14 + Tailwind dashboard (FR-DSH)
│   └── app/
│       ├── page.tsx                #   Main dashboard (mandate, ledger, revoke)
│       ├── layout.tsx              #   Root layout
│       └── types.ts                #   TypeScript interfaces
│
├── docs/
│   ├── PRD.md                      # Product requirements
│   ├── SRS.md                      # Full functional spec (FR-IDs)
│   └── ARCHITECTURE.md             # System design
│
├── AGENTS.md                       # AI coding agent context
├── SUBMISSION.md                   # Buildathon submission details
└── README.md                       # ← You are here
```

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/catalog` | Full product catalog (JSON) |
| `GET` | `/api/state` | Mandate + stats + audit log (dashboard polling) |
| `POST` | `/api/purchase` | Evaluate → execute a purchase (body: `sku_qty_pairs`, `merchant_id`, optional `force_failure`) |
| `POST` | `/api/revoke` | Immediately revoke the spending mandate |

---

## 🧪 Testing

The test suite covers every functional requirement with traceable test names:

```bash
cd backend && pytest -v
```

```
test_FR_INT_1_and_2.py    — Active mandate → approved
test_FR_INT_3.py          — Revoked mandate → MANDATE_REVOKED
test_FR_INT_4.py          — Unknown merchant → SCOPE_MERCHANT
test_FR_INT_5.py          — Blocked category → SCOPE_CATEGORY
test_FR_INT_6.py          — Over per-txn limit → Z8
test_FR_INT_7.py          — Cumulative cap breach → Z8
test_FR_INT_8.py          — Velocity exceeded → U16
test_FR_INT_9.py          — Audit log written for every decision
test_FR_INT_10.py         — Revocation persists
test_FR_INT_11.py         — Unknown SKU → UNKNOWN_SKU
test_FR_CAT_3.py          — Catalog loads correctly
test_FR_MAN_status.py     — Mandate status transitions
test_FR_PAY_1_and_2.py    — Mock payment success + NPCI failures
test_FR_AGT_3_and_5.py    — Blocked = plain language; each failure = distinct message
test_FR_DSH_api.py        — Dashboard API endpoints (state, purchase, revoke)
```

---

## 📖 Documentation

| Document | Purpose |
|:---------|:--------|
| [PRD.md](docs/PRD.md) | Product requirements, goals, personas, risks |
| [SRS.md](docs/SRS.md) | Full functional & non-functional spec with numbered FR-IDs |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, swappable components |
| [AGENTS.md](AGENTS.md) | Context file for AI coding agents working in this repo |
| [SUBMISSION.md](SUBMISSION.md) | Razorpay AI Buildathon submission details |

---

## 🛠️ Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend** | Next.js 14, React 18, Tailwind CSS, TypeScript |
| **Interceptor** | Pure Python — deterministic, zero dependencies on LLM |
| **Payments** | Razorpay MCP server (test mode: `rzp_test_` keys only) |
| **Config** | YAML (mandate rules — editable without code changes) |
| **Testing** | pytest (backend), 15 test files covering all FR-IDs |
| **Tooling** | Built with [OpenCode](https://github.com/opencode-ai/opencode) + NVIDIA NIM free tier |

---

## ⚖️ License

This project was built for the Razorpay AI Buildathon 2026.

---

<p align="center">
  <b>Agents propose. The Interceptor disposes.</b><br/>
  <sub>Built with 🛡️ for the Razorpay AI Buildathon 2026 — Track 1: Agentic Commerce</sub>
</p>
