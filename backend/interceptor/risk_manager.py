"""Deterministic Risk Manager / Interceptor.

Non-negotiable architectural rule (AGENTS.md): this module is pure rule-based
logic. It MUST NOT make any LLM call. No payment execution call may be reached
without first passing through `RiskManager.evaluate()`.

Every check produces a distinct reason code per SRS Appendix A:
  SCOPE_MERCHANT, SCOPE_CATEGORY, MANDATE_REVOKED, UNKNOWN_SKU, Z8, Z9, U16.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from catalog.catalog import load_catalog
from mandate.mandate import load_mandate, revoke as revoke_mandate, save_mandate

AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "audit_log.jsonl"

# Distinct reason codes (SRS Appendix A / FR-INT requirements).
CODE_OK = "OK"
CODE_SCOPE_MERCHANT = "SCOPE_MERCHANT"
CODE_SCOPE_CATEGORY = "SCOPE_CATEGORY"
CODE_MANDATE_REVOKED = "MANDATE_REVOKED"
CODE_UNKNOWN_SKU = "UNKNOWN_SKU"
CODE_Z8 = "Z8"
CODE_Z9 = "Z9"
CODE_U16 = "U16"


class Decision:
    """Outcome of an Interceptor evaluation."""

    __slots__ = ("approved", "code", "reason")

    def __init__(self, approved: bool, code: str, reason: str) -> None:
        self.approved = approved
        self.code = code
        self.reason = reason

    def __repr__(self) -> str:
        return f"Decision(approved={self.approved}, code={self.code}, reason={self.reason!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Decision):
            return NotImplemented
        return (self.approved, self.code, self.reason) == (
            other.approved,
            other.code,
            other.reason,
        )


def default_now() -> datetime:
    return datetime.now(timezone.utc)


def default_append_log(entry: dict, path: Path = AUDIT_LOG_PATH) -> None:
    """Append a single audit entry as one JSON line (append-only, FR-INT-9)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class RiskManager:
    """Deterministic policy enforcement against the active mandate.

    All mutable state (cumulative spend, attempt history) is owned by the
    instance, so it is independent of process-global state and fully available
    to tests. Persistence hooks (mandate loader, audit append) are injectable.
    """

    def __init__(
        self,
        mandate_loader: Callable = load_mandate,
        mandate_writer: Callable = save_mandate,
        catalog_loader: Callable = load_catalog,
        audit_append: Callable = default_append_log,
        now: Callable = default_now,
    ) -> None:
        self._load_mandate = mandate_loader
        self._save_mandate = mandate_writer
        self._load_catalog = catalog_loader
        self._append_log = audit_append
        self._now = now
        # Cumulative approved spend (INR) with the timestamp of that approval,
        # used for the rolling-window check (FR-INT-7).
        self._approved_events: list[tuple[datetime, int]] = []
        self._cumulative_spend: int = 0
        # Timestamps of every evaluated call (approved or blocked) for velocity
        # tracking (FR-INT-8).
        self._attempt_timestamps: list[datetime] = []

    # --- ordering helper -------------------------------------------------

    def _applicable_spend(self, now: datetime, window_hours: int) -> int:
        cutoff = now - timedelta(hours=window_hours)
        return sum(amt for ts, amt in self._approved_events if ts >= cutoff)

    # --- core evaluation --------------------------------------------------

    def evaluate(self, tool_call: dict) -> Decision:
        """Evaluate a payment tool call against the active mandate.

        This is the ONLY entry point by which a decision is produced. It never
        performs any network or LLM call.
        """
        now = self._now()
        mandate = self._load_mandate()
        decision = self._decide(tool_call, mandate, now)

        # Record the attempt for velocity tracking regardless of outcome (FR-INT-8).
        self._attempt_timestamps.append(now)

        # Accumulate cumulative spend only for approved calls (FR-INT-7).
        if decision.approved:
            amount = int(tool_call.get("args", {}).get("amount_inr", 0))
            self._approved_events.append((now, amount))
            self._cumulative_spend += amount

        # Every evaluated call is logged, approved or blocked (FR-INT-9, NFR-2).
        self._append_log(self._build_audit_entry(tool_call, decision, now))

        return decision

    def _decide(self, tool_call: dict, mandate: dict, now: datetime) -> Decision:
        # FR-INT-3: mandate must be active.
        if mandate.get("status") != "active":
            return Decision(False, CODE_MANDATE_REVOKED, "mandate is not active")

        args = tool_call.get("args", {})
        merchant_id = args.get("merchant_id")

        # FR-INT-4: merchant allow-list.
        allowed_merchants = mandate.get("scope", {}).get("allowed_merchants", [])
        if merchant_id not in allowed_merchants:
            return Decision(
                False,
                CODE_SCOPE_MERCHANT,
                f"merchant '{merchant_id}' is not in the mandate allow-list",
            )

        # FR-INT-11: unknown SKU (check before other item-level checks).
        items = args.get("items", [])
        catalog = self._load_catalog()
        known_skus = {p["sku"] for p in catalog.get("products", [])}
        for item in items:
            if item.get("sku") not in known_skus:
                return Decision(
                    False,
                    CODE_UNKNOWN_SKU,
                    f"unrecognized SKU '{item.get('sku')}' in tool call",
                )

        # FR-INT-5: category deny-list (identity offending item + category).
        blocked_categories = mandate.get("scope", {}).get("blocked_categories", [])
        sku_to_category = {p["sku"]: p["category"] for p in catalog.get("products", [])}
        for item in items:
            category = sku_to_category.get(item.get("sku"))
            if category in blocked_categories:
                return Decision(
                    False,
                    CODE_SCOPE_CATEGORY,
                    f"item SKU '{item.get('sku')}' is in denied category '{category}'",
                )

        amount = int(args.get("amount_inr", 0))
        limits = mandate.get("limits", {})

        # FR-INT-6: per-transaction limit (→ Z8).
        max_per_txn = limits.get("max_per_transaction")
        if max_per_txn is not None and amount > max_per_txn:
            return Decision(
                False,
                CODE_Z8,
                f"amount {amount} exceeds per-transaction limit {max_per_txn}",
            )

        # FR-INT-7: cumulative rolling-window limit.
        max_cumulative = limits.get("max_cumulative")
        window_hours = limits.get("cumulative_window_hours") or 24
        applicable = self._applicable_spend(now, window_hours)
        if max_cumulative is not None and applicable + amount > max_cumulative:
            return Decision(
                False,
                CODE_Z8,
                f"amount {amount} would exceed cumulative limit {max_cumulative} "
                f"(already spent {applicable})",
            )

        # FR-INT-8: velocity limit (trailing 60s window, → U16).
        max_per_min = limits.get("max_attempts_per_minute")
        if max_per_min is not None:
            cutoff = now - timedelta(seconds=60)
            recent = [t for t in self._attempt_timestamps if t >= cutoff]
            if len(recent) >= max_per_min:
                return Decision(
                    False,
                    CODE_U16,
                    f"attempt rate exceeds {max_per_min}/minute velocity limit",
                )

        return Decision(True, CODE_OK, "approved")

    def _build_audit_entry(self, tool_call: dict, decision: Decision, now: datetime) -> dict:
        return {
            "timestamp": now.isoformat(),
            "tool_call": tool_call,
            "decision": {
                "approved": decision.approved,
                "code": decision.code,
                "reason": decision.reason,
            },
        }

    # --- revocation (FR-INT-10) ------------------------------------------

    def revoke(self) -> None:
        """Set the mandate to 'revoked' and persist it to the mandate file."""
        mandate = self._load_mandate()
        mandate = revoke_mandate(mandate)
        self._save_mandate(mandate)