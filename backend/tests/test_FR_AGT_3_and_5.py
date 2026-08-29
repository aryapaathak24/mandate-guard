"""Tests for the agent orchestrator (FR-AGT-3, FR-AGT-5)."""

import pytest

from tests.conftest import make_tool_call
from agent.orchestrator import build_cart, attempt_purchase
from mcp_client.razorpay_mock import CODE_Z9, CODE_U30, CODE_U16


def make_cart_pairs():
    return [("RICE-BASMATI-1KG", 1)]


def test_build_cart_matches_tool_call_schema():
    tool_call = build_cart([("RICE-BASMATI-1KG", 2)], "amart-grocers-001")

    assert tool_call["tool"] == "create_payment_intent"
    assert tool_call["args"]["merchant_id"] == "amart-grocers-001"
    assert tool_call["args"]["items"] == [
        {"sku": "RICE-BASMATI-1KG", "qty": 2, "name": "Basmati Rice 1kg"}
    ]
    assert tool_call["args"]["amount_inr"] == 360


class CountingPaymentClient:
    """Wraps the mock payment client and counts execution attempts."""

    def __init__(self):
        self.calls = 0

    def execute_payment(self, tool_call, force_failure=None):
        self.calls += 1
        from mcp_client.razorpay_mock import execute_payment as real_execute

        return real_execute(tool_call, force_failure=force_failure)


def test_FR_AGT_3_blocked_call_never_reaches_payment_client(env, monkeypatch):
    _, build = env
    risk_manager = build()
    client = CountingPaymentClient()

    monkeypatch.setattr("agent.orchestrator.execute_payment", client.execute_payment)

    tool_call = make_tool_call(items=[{"sku": "GIFT-CARD-500", "qty": 1, "name": "Gift Card"}])
    response = attempt_purchase(risk_manager, tool_call)

    assert client.calls == 0
    assert response["ok"] is False
    assert "not allowed" in response["message"]


def _approved_risk_manager(env):
    _, build = env
    return build()


def test_FR_AGT_5_each_failure_code_yields_distinct_message(env, monkeypatch):
    risk_manager = _approved_risk_manager(env)
    tool_call = make_tool_call()

    messages = {}
    for code in (CODE_Z9, CODE_U30, CODE_U16):
        response = attempt_purchase(risk_manager, tool_call, force_failure=code)
        assert response["ok"] is False
        messages[code] = response["message"]

    assert len(set(messages.values())) == 3


def test_FR_AGT_5_success_path_returns_payment_id(env):
    risk_manager = _approved_risk_manager(env)
    tool_call = make_tool_call()

    response = attempt_purchase(risk_manager, tool_call)

    assert response["ok"] is True
    assert response["payment_id"].startswith("pay_")