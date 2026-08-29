"""Agent orchestrator — turns purchase intent into a payment execution.

Currently the ``cart builder`` is deterministic/scripted (no LLM call),
matching the tool_call schema shared by ``interceptor/risk_manager.py``
and ``mcp_client/razorpay_mock.py`` (FR-AGT-1).

The payment path is strictly Interceptor-first (FR-AGT-2, NFR-1): a tool
call must pass ``RiskManager.evaluate()`` before ``execute_payment`` is
ever reached, no exceptions.

FR-AGT-3: blocked calls are answered in plain language and never reach
the payment client.
FR-AGT-5: each execution failure code maps to a distinct message.
FR-AGT-6: no automatic retry — one attempt per explicit call.
"""

from __future__ import annotations

from catalog.catalog import load_catalog
from mcp_client.razorpay_mock import (
    PaymentResult,
    execute_payment,
    CODE_Z9,
    CODE_U30,
    CODE_U16,
)


def build_cart(sku_qty_pairs: list[tuple[str, int]], merchant_id: str) -> dict:
    """Build a ``create_payment_intent`` tool_call from SKU/qty pairs.

    Deterministic and LLM-free (FR-AGT-1): looks up name and price from the
    read-only catalog and totals the amount in INR.
    """
    catalog = load_catalog()
    products = {p["sku"]: p for p in catalog.get("products", [])}

    items = []
    amount = 0
    for sku, qty in sku_qty_pairs:
        product = products[sku]
        items.append({"sku": sku, "qty": qty, "name": product["name"]})
        amount += product["price_inr"] * qty

    return {
        "tool": "create_payment_intent",
        "args": {
            "merchant_id": merchant_id,
            "items": items,
            "amount_inr": amount,
        },
    }


# Distinct, plain-language user-facing messages per failure code (FR-AGT-5).
_FAILURE_MESSAGES = {
    CODE_Z9: "Your account has insufficient funds for this purchase. "
    "Please top up your balance or choose a cheaper alternative.",
    CODE_U30: "The bank's system is currently down, so the payment couldn't go through. "
    "Please try again in a little while.",
    CODE_U16: "This transaction was blocked for security reasons. "
    "Please contact support to review your account.",
}


def attempt_purchase(risk_manager, tool_call: dict, force_failure: str | None = None) -> dict:
    """Evaluate, then (only if approved) execute one payment attempt.

    Returns a user-facing dict (never raw internal error text) with:
      - ``ok``: whether the user should treat the purchase as succeeded
      - ``message``: plain-language explanation of what happened.

    The payment client is only reached on an approved tool call (FR-AGT-3),
    and a failed execution is never retried automatically (FR-AGT-6).
    """
    decision = risk_manager.evaluate(tool_call)

    if not decision.approved:
        return {
            "ok": False,
            "message": "This purchase was not allowed. "
            f"{decision.reason}.",
        }

    result: PaymentResult = execute_payment(tool_call, force_failure=force_failure)

    if result.success:
        return {
            "ok": True,
            "message": f"Payment completed. Your payment ID is {result.payment_id}.",
            "payment_id": result.payment_id,
        }

    return {
        "ok": False,
        "message": _FAILURE_MESSAGES.get(
            result.code,
            f"Payment failed with reason code {result.code}.",  # non-generic fallback
        ),
        "code": result.code,
    }