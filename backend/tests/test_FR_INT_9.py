from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_SCOPE_MERCHANT


def test_FR_INT_9_logs_every_evaluated_call(env):
    state, build = env
    rm = build()

    # One approved call.
    rm.evaluate(make_tool_call())

    # One blocked call (disallowed merchant).
    rm.evaluate(make_tool_call(merchant_id="evil-mart-999"))

    assert len(state["audit"]) == 2

    approved_entry = state["audit"][0]
    assert approved_entry["decision"]["approved"] is True
    assert "timestamp" in approved_entry
    assert "tool_call" in approved_entry
    assert "code" in approved_entry["decision"]
    assert "reason" in approved_entry["decision"]

    blocked_entry = state["audit"][1]
    assert blocked_entry["decision"]["approved"] is False
    assert blocked_entry["decision"]["code"] == CODE_SCOPE_MERCHANT