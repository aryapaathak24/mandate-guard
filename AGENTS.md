# AGENTS.md — Agentic Guard

This file is the primary context reference for AI coding agents working in
this repo — OpenCode, Cline, Aider, Antigravity CLI, or any other. Keep it
accurate; it is the single source of truth for how to work in this codebase.
Update it whenever architecture or conventions change.

> Tooling note: this project is built using **OpenCode** (free, open-source,
> terminal-native) with a **free NVIDIA NIM API key** (`nvapi-...`) serving
> `deepseek-ai/deepseek-v4-pro` as the model. No paid coding tool required.
> NVIDIA's free tier has a finite credit pool (~1000 credits on signup) — see
> "Model usage discipline" below before starting large multi-file tasks.

## Model usage discipline (NVIDIA free tier is not unlimited)

- Prefer small, single-file, single-FR-ID requests over "implement the whole
  module" requests — this burns fewer credits per call and produces safer,
  reviewable diffs anyway (see the vibe-coding workflow in this file).
- If a request needs broad codebase context (e.g. a refactor touching many
  files), consider whether a cheaper/smaller model in OpenCode's config
  could do it, reserving deepseek-v4-pro for genuinely hard implementation
  passes (interceptor logic, agent tool-use loop).
- If credits run low mid-build, Antigravity CLI (free for individuals, no
  credit metering) is the fallback — see prior conversation for setup.
- Check remaining credits periodically at build.nvidia.com before starting
  a work session, so you're not cut off mid-task.

## What this project is

A demonstration system for the Razorpay AI Buildathon (Track 1: Agentic
Commerce). An AI agent completes UPI-style purchases via Razorpay's MCP
server, but every payment tool call is validated by a deterministic
Risk Manager / Interceptor against a spending mandate BEFORE execution.

Full requirements: see `/docs/PRD.md` (product) and `/docs/SRS.md`
(technical spec with numbered FR-IDs — e.g. FR-INT-6). When implementing
a feature, cite the FR-ID it satisfies in the commit message and in a
comment near the implementing code.

## Non-negotiable architectural rule

The Interceptor is deterministic, rule-based logic — NEVER an LLM call.
No payment execution call may ever be reachable without first passing
through `interceptor.risk_manager.RiskManager.evaluate()`. If you are
asked to add a new payment path, route it through the Interceptor first,
no exceptions, even for "just testing."

## Tech stack (do not deviate without discussion)

- Backend: Python 3.11+, FastAPI
- Agent/LLM: Anthropic SDK, raw tool-use loop (no LangChain/LangGraph)
- Database: Postgres via Supabase
- Frontend: Next.js + Tailwind
- Payments: Razorpay MCP server (test mode: `rzp_test_` keys only —
  NEVER production keys in this repo, in code, or in commits)
- Testing: pytest (backend), Playwright (dashboard visual/e2e)

## Repo structure

```
/backend
  /catalog        - product catalog data + llms.txt
  /mandate         - mandate schema + Supabase access layer
  /interceptor     - risk_manager.py (the core deterministic logic)
  /agent           - orchestrator.py (LLM tool-use loop)
  /mcp_client      - razorpay_mock.py + razorpay_real.py (same interface)
  /tests           - pytest, named test_<FR-ID>_<description>
/frontend          - Next.js dashboard
/docs
  PRD.md
  SRS.md
  ARCHITECTURE.md
  API.md
```

## Conventions

- Every Interceptor rejection must produce a specific `code` (see SRS
  Appendix A for the full code list: Z8, Z9, U16, U30, SCOPE_CATEGORY,
  SCOPE_MERCHANT, MANDATE_REVOKED, UNKNOWN_SKU). Never return a generic
  "blocked" with no code.
- Every tool call, approved or blocked, must be logged. No silent paths.
- Mandate and policy values live in config (YAML/DB), never hardcoded
  in application logic.
- Mock and real payment clients must share an identical function
  signature so they are interchangeable with a one-line swap.
- Commit small and often. One logical change per commit. Reference the
  FR-ID in the message, e.g. `feat(interceptor): enforce cumulative
  cap (FR-INT-7)`.

## Commands

```bash
# backend
cd backend && uvicorn main:app --reload

# tests
cd backend && pytest -v

# frontend
cd frontend && npm run dev

# db migrations
supabase db push
```

## What "done" means for a feature

1. Implements the exact FR-ID(s) from SRS.md — no more, no less scope.
2. Has a passing pytest test named after that FR-ID.
3. Produces an audit log entry if it touches a payment decision.
4. Does not require a code change to adjust policy values (config-driven).

## Known open questions (do not silently assume — ask)

- Submission deadline is not yet confirmed — do not assume timeline.
- Whether cart parsing uses a real LLM call or stays scripted is not
  finalized — check before touching `agent/orchestrator.py` cart logic.
