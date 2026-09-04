"""API-level tests (FR-DSH / FR-INT-7 shared-instance persistence).

Proves that the module-level RiskManager keeps cumulative spend across
multiple /api/purchase calls in a single test client session — i.e. the
shared instance actually holds state, rather than being reset per request.
"""

from fastapi.testclient import TestClient

import main


def _fresh_risk_manager(state, monkeypatch):
    from tests.conftest import make_mandate, make_catalog

    state["mandate"] = make_mandate()
    state["mandate"]["limits"]["max_cumulative"] = 1000
    state["mandate"]["limits"]["max_per_transaction"] = 2000
    state["catalog"] = make_catalog()
    state["audit"] = []

    from interceptor.risk_manager import RiskManager

    def loader():
        return state["mandate"]

    def writer(m):
        state["mandate"] = m

    def cat():
        return state["catalog"]

    def append(entry):
        state["audit"].append(entry)

    monkeypatch.setattr(main, "_read_audit_log", lambda: list(reversed(state["audit"])))

    return RiskManager(
        mandate_loader=loader,
        mandate_writer=writer,
        catalog_loader=cat,
        audit_append=append,
    )


def test_shared_instance_preserves_cumulative_spend(monkeypatch):
    state = {}

    shared_rm = _fresh_risk_manager(state, monkeypatch)
    monkeypatch.setattr(main, "risk_manager", shared_rm)

    # Make /api/state read stats from the shared instance (not the frozen
    # value at import), and log to the in-memory list.
    monkeypatch.setattr(main, "risk_manager", shared_rm)

    client = TestClient(main.app)

    # Two purchases: first 900 INR (approved), second 180 INR would push
    # cumulative to 1080 > 1000 cap, so it must be blocked. This proves the
    # shared-instance state persisted across calls rather than resetting.
    first = client.post(
        "/api/purchase",
        json={"sku_qty_pairs": [["RICE-BASMATI-1KG", 5]], "merchant_id": "amart-grocers-001"},
    )
    assert first.status_code == 200
    assert first.json()["ok"] is True

    state_resp = client.get("/api/state").json()
    assert state_resp["stats"]["total_spend_inr"] == 900
    assert state_resp["stats"]["approved_count"] == 1

    second = client.post(
        "/api/purchase",
        json={"sku_qty_pairs": [["RICE-BASMATI-1KG", 1]], "merchant_id": "amart-grocers-001"},
    )
    assert second.status_code == 200
    assert second.json()["ok"] is False

    state_resp = client.get("/api/state").json()
    assert state_resp["stats"]["approved_count"] == 1
    assert state_resp["stats"]["blocked_count"] == 1
    assert state_resp["stats"]["total_spend_inr"] == 900


def test_revoke_via_api(monkeypatch):
    """Test immediate mandate revocation via API (FR-DSH-5 / FR-INT-10)."""
    state = {}
    shared_rm = _fresh_risk_manager(state, monkeypatch)
    monkeypatch.setattr(main, "risk_manager", shared_rm)

    client = TestClient(main.app)

    resp = client.post("/api/revoke")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert state["mandate"]["status"] == "revoked"


def test_category_blocked_via_api(monkeypatch):
    state = {}
    shared_rm = _fresh_risk_manager(state, monkeypatch)
    monkeypatch.setattr(main, "risk_manager", shared_rm)

    client = TestClient(main.app)

    # Attempt purchasing a product in denied category 'Gift Cards' (FR-INT-5 / FR-DSH-3)
    resp = client.post(
        "/api/purchase",
        json={"sku_qty_pairs": [["GC-AMAZON-500", 1]], "merchant_id": "amart-grocers-001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "Gift Cards" in data["message"]
    assert "GC-AMAZON-500" in data["message"]

    # Verify state updates blocked_count and logs the audit entry (FR-DSH-2, FR-DSH-3)
    state_resp = client.get("/api/state").json()
    assert state_resp["stats"]["blocked_count"] == 1
    assert state_resp["stats"]["approved_count"] == 0
    assert state_resp["stats"]["total_spend_inr"] == 0
    assert len(state_resp["audit_log"]) == 1
    assert state_resp["audit_log"][0]["decision"]["code"] == "SCOPE_CATEGORY"


def test_get_catalog_via_api():
    """Test read-only catalog endpoint returns structured products (FR-CAT-1)."""
    client = TestClient(main.app)
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "merchant_id" in data
    assert "products" in data
    assert len(data["products"]) > 0
    first = data["products"][0]
    assert "sku" in first
    assert "name" in first
    assert "price_inr" in first
    assert "category" in first