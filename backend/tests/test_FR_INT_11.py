from tests.conftest import make_tool_call
from interceptor.risk_manager import CODE_UNKNOWN_SKU


def test_FR_INT_11_rejects_unknown_sku(env):
    state, build = env
    rm = build()

    result = rm.evaluate(
        make_tool_call(
            items=[{"sku": "NONEXISTENT-SKU", "qty": 1, "name": "Mystery"}],
            amount_inr=100,
        )
    )

    assert result.approved is False
    assert result.code == CODE_UNKNOWN_SKU
    assert "NONEXISTENT-SKU" in result.reason