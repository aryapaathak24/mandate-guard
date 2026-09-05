"""Agentic Guard backend entrypoint (FR-DSH-* / FR-INT-7 / FR-INT-8).

The ``RiskManager`` is instantiated ONCE at module import time and shared
across every request. Cumulative spend and velocity tracking live in
instance memory (FR-INT-7, FR-INT-8); recreating the manager per-request
would silently reset those counters and break mandate enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.orchestrator import build_cart, attempt_purchase
from catalog.catalog import load_catalog
from interceptor.risk_manager import RiskManager, AUDIT_LOG_PATH
from mandate.mandate import load_mandate

app = FastAPI(title="Agentic Guard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared instance — module-level, created once at startup.
risk_manager = RiskManager()

MAX_AUDIT_ENTRIES = 200


class PurchaseRequest(BaseModel):
    sku_qty_pairs: list[tuple[str, int]]
    merchant_id: str
    force_failure: str | None = None


def _read_audit_log(limit: int = MAX_AUDIT_ENTRIES) -> list[dict]:
    """Return up to ``limit`` most recent audit entries, newest first."""
    import json

    if not AUDIT_LOG_PATH.exists():
        return []

    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    entries = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            entries.append(json.loads(line_str))
        except Exception:
            continue
    return list(reversed(entries[-limit:]))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/catalog")
def get_catalog() -> dict:
    """Return the read-only product catalog for agent/UI selection (FR-CAT-1)."""
    return load_catalog()


@app.get("/api/state")
def get_state() -> dict:
    mandate = load_mandate()
    stats = risk_manager.get_stats()

    return {
        "mandate": mandate,
        "stats": {
            **stats,
            "cumulative_limit_inr": mandate.get("limits", {}).get("max_cumulative"),
        },
        "audit_log": _read_audit_log(),
    }


@app.post("/api/purchase")
def purchase(request: PurchaseRequest) -> dict:
    tool_call = build_cart(request.sku_qty_pairs, request.merchant_id)
    return attempt_purchase(
        risk_manager,
        tool_call,
        force_failure=request.force_failure,
    )


@app.post("/api/revoke")
def revoke() -> dict:
    risk_manager.revoke()
    return {
        "ok": True,
        "message": "Mandate has been revoked.",
        "mandate_id": load_mandate().get("mandate_id"),
    }


@app.post("/api/reset")
def reset_state() -> dict:
    """Reset session statistics and restore mandate to active (for demo repeatability)."""
    risk_manager.reset()
    return {
        "ok": True,
        "message": "Mandate reset to active and session statistics cleared.",
        "mandate": load_mandate(),
    }