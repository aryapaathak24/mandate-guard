# Razorpay AI Builder Internship 2026 - Submission Details

Here are the official answers used for the Google Form final submission.

**Selected Track**
Track 1: Agentic Commerce

**Project Name / Title**
Agentic Guard (Mandate-Bounded Risk Interceptor)

**Project Objectives (What does it solve?)**
Agentic Guard solves the critical trust and security barrier preventing the widespread adoption of autonomous AI agents in commerce. While LLMs are excellent at understanding intent and building shopping carts, they are inherently susceptible to hallucinations and prompt injections. 

This project solves that by introducing a strict, deterministic "Interceptor" layer. It ensures that an AI agent (powered by the Anthropic SDK) can propose tool calls, but those calls are strictly evaluated against a rigid, local "spending mandate" (YAML) before ever reaching the Razorpay MCP server. It guarantees that an agent cannot exceed authorized transaction/cumulative limits, purchase from blocked categories (like Gift Cards or Alcohol), or bypass velocity limits, ensuring 100% safe, human-overseen agentic commerce.

**GitHub Repository URL**
https://github.com/manav-Mnv/mandate-guard

**5-min Pitch Video Link**
[Insert Link Here]

**Build Challenges & Technical Obstacles (What issues did you face while building, and how did you solve them?)**
1. **Architectural Separation of Concerns:** The biggest challenge was ensuring the AI could never "talk its way out" of the rules. We solved this by strictly separating the AI orchestrator from the rules engine. The `RiskManager` was built as a purely deterministic Python layer; it intercepts the LLM's payload, validates it synchronously against the local `mandate.yaml`, and assigns a strict reason code (e.g., Z8, SCOPE_CATEGORY) before the Razorpay client is even invoked.
2. **Real-time Human Oversight & State Synchronization:** We needed a way for a user to monitor an autonomous agent and pull the plug instantly if it went rogue. We solved this by building a Next.js dashboard that polls a FastAPI backend `/api/state` endpoint. The backend synchronously writes every Interceptor decision to an append-only `audit_log.jsonl` ledger. The dashboard provides a "Revoke Access" emergency button that instantly flips the mandate status, mechanically disabling both the UI and the backend's ability to execute further payments.
3. **Simulating Edge Cases Safely:** Testing financial edge cases (insufficient funds, velocity limits) without burning real API calls or risking real credentials was difficult. We solved this by building a `razorpay_mock.py` client that perfectly mirrors the signature of the real Razorpay MCP server. This allowed us to build an exhaustive, 30-test pytest suite proving the Interceptor's resilience against complex failure scenarios locally before integration.
