from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_MANDATE_REVOKED


def test_FR_INT_3_rejects_inactive_mandate(env):
    state, build = env
    state["mandate"]["status"] = "revoked"
    rm = build()

    result = rm.evaluate(make_tool_call())

    assert result.approved is False
    assert result.code == CODE_MANDATE_REVOKED