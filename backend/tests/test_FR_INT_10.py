def test_FR_INT_10_revoke_persists_to_mandate(env):
    state, build = env
    rm = build()

    assert state["mandate"]["status"] == "active"

    rm.revoke()

    assert state["mandate"]["status"] == "revoked"
    assert state["mandate"]["revoked_at"] is not None