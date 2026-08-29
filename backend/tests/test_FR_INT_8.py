from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_U16


def test_FR_INT_8_enforces_velocity_limit(env):
    state, build = env
    state["mandate"]["limits"]["max_attempts_per_minute"] = 2
    rm = build()

    first = rm.evaluate(make_tool_call(amount_inr=10))
    second = rm.evaluate(make_tool_call(amount_inr=10))
    assert first.approved is True
    assert second.approved is True

    # Third attempt within trailing 60s exceeds the velocity limit.
    third = rm.evaluate(make_tool_call(amount_inr=10))
    assert third.approved is False
    assert third.code == CODE_U16