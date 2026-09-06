#!/usr/bin/env python3
"""Manual smoke-test: create ONE real test-mode Razorpay payment link.

Run this by hand to confirm the real client actually talks to Razorpay's
sandbox — the output is a live payment link you can open in a browser.

Usage
-----
    cd backend
    python -m scripts.test_real_razorpay

Prerequisites
-------------
- ``backend/.env`` must contain ``RAZORPAY_KEY_ID`` (must start with
  ``rzp_test_``) and ``RAZORPAY_KEY_SECRET``.
- ``razorpay`` must be installed (``pip install -r requirements.txt``).

This script is NOT a pytest test and is NOT run automatically.
"""

from __future__ import annotations

import sys
import os

# Ensure the backend/ directory is on sys.path so imports work when
# running with ``python -m scripts.test_real_razorpay`` from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# --- This import will fail-fast if credentials are missing/invalid ---
from mcp_client.razorpay_real import execute_payment  # noqa: E402


def main() -> None:
    """Create a single test-mode payment link and print the result."""
    tool_call = {
        "amount": 100_00,  # Rs 100 in paise
        "currency": "INR",
        "description": "Agentic Guard - manual smoke test",
        "customer": {
            "name": "Test User",
            "email": "test@example.com",
            "contact": "+919876543210",
        },
    }

    print("Creating a test-mode Razorpay payment link ...")
    result = execute_payment(tool_call)

    print()
    print("=" * 60)
    print(f"  success    : {result.success}")
    print(f"  code       : {result.code}")
    print(f"  message    : {result.message}")
    print(f"  payment_id : {result.payment_id}")
    print("=" * 60)

    if result.success:
        print("\n[OK]  Payment link created successfully.")
        print("    Open the URL in your browser to see the Razorpay checkout page.")
    else:
        print("\n[FAIL]  Payment link creation failed - see details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
