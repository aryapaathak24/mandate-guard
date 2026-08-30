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


def test_FR_INT_7_get_stats(env):
    state, build = env
    state["mandate"]["limits"]["max_cumulative"] = 1000
    rm = build()

    # Initial stats should be zeroed
    stats = rm.get_stats()
    assert stats == {"approved_count": 0, "blocked_count": 0, "total_spend_inr": 0}

    # One approved call
    rm.evaluate(make_tool_call(amount_inr=500))
    # One blocked call (over remaining cumulative cap)
    rm.evaluate(make_tool_call(amount_inr=600))

    stats = rm.get_stats()
    assert stats == {
        "approved_count": 1,
        "blocked_count": 1,
        "total_spend_inr": 500,
    }