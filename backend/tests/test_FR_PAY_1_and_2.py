"""Tests for the mock payment client (FR-PAY-1, FR-PAY-2)."""

import pytest

from tests.conftest import make_tool_call
from mcp_client.razorpay_mock import (
    PaymentResult,
    execute_payment,
    CODE_Z9,
    CODE_U30,
    CODE_U16,
)


def test_FR_PAY_1_returns_structured_success_result():
    result = execute_payment(make_tool_call())

    assert isinstance(result, PaymentResult)
    assert result.success is True
    assert result.code is None
    assert result.message
    assert isinstance(result.payment_id, str) and result.payment_id.startswith("pay_")


def test_FR_PAY_1_returns_structured_failure_shape():
    result = execute_payment(make_tool_call(), force_failure=CODE_Z9)

    assert isinstance(result, PaymentResult)
    assert result.success is False
    assert result.code == CODE_Z9
    assert result.message
    assert result.payment_id is None


def test_FR_PAY_2_simulates_Z9_insufficient_funds():
    result = execute_payment(make_tool_call(), force_failure=CODE_Z9)

    assert result.success is False
    assert result.code == CODE_Z9
    assert result.payment_id is None


def test_FR_PAY_2_simulates_U30_bank_system_down():
    result = execute_payment(make_tool_call(), force_failure=CODE_U30)

    assert result.success is False
    assert result.code == CODE_U30
    assert result.payment_id is None


def test_FR_PAY_2_simulates_U16_security_block():
    result = execute_payment(make_tool_call(), force_failure=CODE_U16)

    assert result.success is False
    assert result.code == CODE_U16
    assert result.payment_id is None


def test_unknown_force_failure_raises():
    with pytest.raises(ValueError):
        execute_payment(make_tool_call(), force_failure="NOT_A_CODE")