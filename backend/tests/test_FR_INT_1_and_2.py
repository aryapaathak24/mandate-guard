from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_OK


def test_FR_INT_1_evaluates_before_execution(env):
    """evaluate() returns a decision; payment execution never happens here."""
    state, build = env
    rm = build()

    result = rm.evaluate(make_tool_call())

    assert result.approved is True
    assert result.code == CODE_OK


def test_FR_INT_2_is_deterministic_no_llm(env):
    """Same mandate + tool call => identical, reproducible decision."""
    state, build = env
    rm = build()

    first = rm.evaluate(make_tool_call())
    second = rm.evaluate(make_tool_call())

    assert first == second
    assert first.approved is True