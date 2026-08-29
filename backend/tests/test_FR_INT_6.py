from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_Z8


def test_FR_INT_6_rejects_amount_over_per_transaction_limit(env):
    state, build = env
    rm = build()

    result = rm.evaluate(make_tool_call(amount_inr=1500))

    assert result.approved is False
    assert result.code == CODE_Z8