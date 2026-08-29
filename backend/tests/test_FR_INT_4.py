from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_SCOPE_MERCHANT


def test_FR_INT_4_rejects_disallowed_merchant(env):
    state, build = env
    rm = build()

    result = rm.evaluate(make_tool_call(merchant_id="evil-mart-999"))

    assert result.approved is False
    assert result.code == CODE_SCOPE_MERCHANT