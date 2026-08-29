"""Mock Razorpay payment client.

Simulates the Razorpay MCP server's ``create_payment_intent`` tool call
with a deterministic result. Swap this for ``razorpay_real.py`` (same
``execute_payment`` interface) when real test-mode integration is in
place — the Interceptor and Orchestrator must never need to change.

FR-PAY-1 / FR-PAY-2.
"""

from dataclasses import dataclass
import itertools
import uuid


CODE_Z9 = "Z9"     # insufficient funds (FR-PAY-2)
CODE_U30 = "U30"   # bank system down (FR-PAY-2)
CODE_U16 = "U16"   # security block (FR-PAY-2)

_MESSAGES = {
    CODE_Z9: "Insufficient funds in remitter account.",
    CODE_U30: "Bank system down; debit failed.",
    CODE_U16: "Transaction blocked for security reasons.",
}


@dataclass
class PaymentResult:
    """Structured outcome from a payment execution call."""

    success: bool
    code: str | None
    message: str
    payment_id: str | None


_payment_id_counter = itertools.count(1)


def _fake_payment_id() -> str:
    """Deterministic, collision-free fake payment ID (prefixed with pay_,
    never a real Razorpay id, never a production key)."""
    return f"pay_mock_{uuid.uuid4().hex[:16]}"


def execute_payment(tool_call: dict, force_failure: str | None = None) -> PaymentResult:
    """Simulate Razorpay ``create_payment_intent``.

    ``force_failure`` may be one of ``Z9``, ``U30``, ``U16`` (or ``None``
    for success) to deterministically drive a specific outcome for testing
    and demos (FR-PAY-2).
    """
    if force_failure is None:
        return PaymentResult(
            success=True,
            code=None,
            message="Payment succeeded.",
            payment_id=_fake_payment_id(),
        )

    if force_failure in _MESSAGES:
        return PaymentResult(
            success=False,
            code=force_failure,
            message=_MESSAGES[force_failure],
            payment_id=None,
        )

    raise ValueError(
        f"Unknown force_failure code: {force_failure!r}. "
        f"Expected one of {list(_MESSAGES)} or None."
    )