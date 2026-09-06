"""Real Razorpay payment client (test-mode only).

Implements the identical ``execute_payment(tool_call, force_failure=None)
-> PaymentResult`` interface as ``razorpay_mock.py`` so the Interceptor and
Orchestrator never need to change when swapping implementations (see
docs/ARCHITECTURE.md — Swappable Components).

**force_failure is NOT supported in the real client.**  That parameter exists
solely for the mock's deterministic testing/demo mode.  Passing any value
other than ``None`` raises ``TypeError`` — the parameter is retained in the
signature only for interface compatibility, not silently accepted and ignored.

Credentials are loaded from environment variables ``RAZORPAY_KEY_ID`` and
``RAZORPAY_KEY_SECRET`` (via ``python-dotenv`` if a ``.env`` file is present).
They are never hardcoded, never logged, and never printed.  If either is
missing at module-load time, a clear ``RuntimeError`` is raised immediately
rather than failing silently on the first API call.

Only ``rzp_test_`` key IDs are accepted — production keys are rejected at
startup as a safety guardrail.

FR-PAY-1 / FR-PAY-2.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import razorpay  # razorpay Python SDK — see backend/requirements.txt

# ---------------------------------------------------------------------------
# Logging — audit-grade, never to stdout
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export the same PaymentResult + code constants used by razorpay_mock.py
# so consumers can import from either module interchangeably.
# ---------------------------------------------------------------------------
CODE_Z9 = "Z9"    # insufficient funds
CODE_U30 = "U30"  # bank system down
CODE_U16 = "U16"  # security block
CODE_RAZORPAY_ERROR = "RAZORPAY_ERROR"  # generic unmapped Razorpay failure

_MESSAGES = {
    CODE_Z9: "Insufficient funds in remitter account.",
    CODE_U30: "Bank system down; debit failed.",
    CODE_U16: "Transaction blocked for security reasons.",
    CODE_RAZORPAY_ERROR: "Payment failed due to a Razorpay error.",
}


@dataclass
class PaymentResult:
    """Structured outcome from a payment execution call."""

    success: bool
    code: str | None
    message: str
    payment_id: str | None


# ---------------------------------------------------------------------------
# Credential loading — fail fast, never leak
# ---------------------------------------------------------------------------
# python-dotenv is optional; if a .env file exists it will be loaded.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # fall through to os.environ

_KEY_ID: str = os.environ.get("RAZORPAY_KEY_ID", "")
_KEY_SECRET: str = os.environ.get("RAZORPAY_KEY_SECRET", "")

if not _KEY_ID or not _KEY_SECRET:
    raise RuntimeError(
        "Missing required environment variables: RAZORPAY_KEY_ID and/or "
        "RAZORPAY_KEY_SECRET.  Set them in backend/.env or export them in "
        "your shell before importing this module."
    )

if not _KEY_ID.startswith("rzp_test_"):
    raise RuntimeError(
        "RAZORPAY_KEY_ID does not start with 'rzp_test_'. "
        "Production keys are NEVER allowed in this codebase.  "
        "Use a test-mode key only."
    )

# Instantiate client once at module level (connection pooling).
_client = razorpay.Client(auth=(_KEY_ID, _KEY_SECRET))

# ---------------------------------------------------------------------------
# Razorpay error → PaymentResult code mapping
# ---------------------------------------------------------------------------
# Razorpay's API returns error descriptions/codes that don't map 1-to-1 to
# NPCI response codes, but we map where there's a genuine semantic equivalent.
_RAZORPAY_ERROR_MAP: dict[str, str] = {
    # Razorpay "reason" strings (from their error payload)
    "INSUFFICIENT_FUNDS":     CODE_Z9,
    "insufficient_funds":     CODE_Z9,
    "BANK_UNAVAILABLE":       CODE_U30,
    "bank_unavailable":       CODE_U30,
    "BLOCKED":                CODE_U16,
    "SECURITY_BLOCK":         CODE_U16,
    "security_block":         CODE_U16,
    "FRAUD_RISK":             CODE_U16,
}


def _map_razorpay_error(error: razorpay.errors.BadRequestError | Exception) -> tuple[str, str]:
    """Extract a PaymentResult (code, message) from a Razorpay SDK exception.

    Returns the mapped NPCI-style code if one exists, otherwise falls back
    to CODE_RAZORPAY_ERROR.  The raw error is logged to the audit logger
    (never printed to stdout).
    """
    raw_message = str(error)

    # razorpay SDK exceptions may carry a .args with structured info
    for razorpay_reason, our_code in _RAZORPAY_ERROR_MAP.items():
        if razorpay_reason in raw_message:
            logger.warning(
                "Razorpay API error mapped to %s: %s", our_code, raw_message,
            )
            return our_code, _MESSAGES.get(our_code, raw_message)

    # No direct mapping — use generic code, log the raw error for audit
    logger.error(
        "Unmapped Razorpay API error (code=%s): %s",
        CODE_RAZORPAY_ERROR, raw_message,
    )
    return CODE_RAZORPAY_ERROR, f"Razorpay error: {raw_message}"


# ---------------------------------------------------------------------------
# Public interface — must match razorpay_mock.execute_payment exactly
# ---------------------------------------------------------------------------

def execute_payment(
    tool_call: dict,
    force_failure: str | None = None,
) -> PaymentResult:
    """Create a real Razorpay payment link via the test-mode API.

    Parameters
    ----------
    tool_call : dict
        Must contain at least ``amount`` (in paise, int) and ``currency``
        (e.g. ``"INR"``).  Optional keys: ``description``, ``customer``
        (dict with ``name``, ``email``, ``contact``).
    force_failure : None
        **NOT SUPPORTED in the real client.**  This parameter exists only
        for interface compatibility with ``razorpay_mock.py``.  Passing
        any value other than ``None`` raises ``TypeError``.

    Returns
    -------
    PaymentResult
        Same dataclass as ``razorpay_mock.PaymentResult`` — fields:
        ``success``, ``code``, ``message``, ``payment_id``.
    """
    if force_failure is not None:
        raise TypeError(
            "force_failure is not supported in the real Razorpay client.  "
            "That parameter only makes sense for the mock implementation.  "
            "Received: force_failure={!r}".format(force_failure)
        )

    # Build the payment link payload from tool_call
    amount = tool_call.get("amount")
    currency = tool_call.get("currency", "INR")
    description = tool_call.get("description", "Agentic Guard payment")

    if amount is None:
        return PaymentResult(
            success=False,
            code=CODE_RAZORPAY_ERROR,
            message="Missing 'amount' in tool_call payload.",
            payment_id=None,
        )

    payload: dict = {
        "amount": int(amount),  # paise
        "currency": currency,
        "description": description,
        "payment_link": {  # not nested — top-level for the SDK
        },
    }

    # Optional customer info
    customer = tool_call.get("customer")
    if customer and isinstance(customer, dict):
        payload["customer"] = {
            k: v for k, v in customer.items()
            if k in ("name", "email", "contact") and v
        }

    try:
        # Razorpay SDK: create a payment link (test mode)
        # Docs: https://razorpay.com/docs/api/payments/payment-links/
        link_payload = {
            "amount": int(amount),
            "currency": currency,
            "description": description,
        }
        if customer and isinstance(customer, dict):
            link_payload["customer"] = {
                k: v for k, v in customer.items()
                if k in ("name", "email", "contact") and v
            }

        response = _client.payment_link.create(link_payload)

        payment_link_id = response.get("id", "")
        short_url = response.get("short_url", "")

        logger.info(
            "Razorpay payment link created: id=%s url=%s",
            payment_link_id, short_url,
        )

        return PaymentResult(
            success=True,
            code=None,
            message=f"Payment link created: {short_url}",
            payment_id=payment_link_id,
        )

    except razorpay.errors.BadRequestError as exc:
        code, message = _map_razorpay_error(exc)
        return PaymentResult(
            success=False,
            code=code,
            message=message,
            payment_id=None,
        )
    except razorpay.errors.ServerError as exc:
        logger.error("Razorpay server error: %s", exc)
        return PaymentResult(
            success=False,
            code=CODE_U30,
            message=_MESSAGES[CODE_U30],
            payment_id=None,
        )
    except razorpay.errors.GatewayError as exc:
        logger.error("Razorpay gateway error: %s", exc)
        return PaymentResult(
            success=False,
            code=CODE_U30,
            message=_MESSAGES[CODE_U30],
            payment_id=None,
        )
    except razorpay.errors.SignatureVerificationError as exc:
        logger.error("Razorpay signature verification error: %s", exc)
        return PaymentResult(
            success=False,
            code=CODE_RAZORPAY_ERROR,
            message="Razorpay signature verification failed.",
            payment_id=None,
        )
    except Exception as exc:  # noqa: BLE001 — catch-all for unexpected SDK errors
        code, message = _map_razorpay_error(exc)
        return PaymentResult(
            success=False,
            code=code,
            message=message,
            payment_id=None,
        )
