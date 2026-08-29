from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_OK, CODE_Z8


def test_FR_INT_7_enforces_cumulative_limit(env):
    state, build = env
    state["mandate"]["limits"]["max_cumulative"] = 1000
    rm = build()

    # First approved call: 600 stays under 1000.
    first = rm.evaluate(make_tool_call(amount_inr=600))
    assert first.approved is True
    assert first.code == CODE_OK

    # Second call would push cumulative to 1200 > 1000.
    second = rm.evaluate(make_tool_call(amount_inr=600))
    assert second.approved is False
    assert second.code == CODE_Z8