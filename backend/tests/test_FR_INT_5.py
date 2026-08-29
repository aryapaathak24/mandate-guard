from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_SCOPE_CATEGORY


def test_FR_INT_5_rejects_blocked_category(env):
    state, build = env
    rm = build()

    result = rm.evaluate(
        make_tool_call(
            items=[{"sku": "GIFT-CARD-500", "qty": 1, "name": "Gift Card 500"}],
            amount_inr=500,
        )
    )

    assert result.approved is False
    assert result.code == CODE_SCOPE_CATEGORY
    assert "GIFT-CARD-500" in result.reason
    assert "Gift Cards" in result.reason