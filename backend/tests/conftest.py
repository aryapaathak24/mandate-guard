"""Shared fixtures for Interceptor tests.

Provides in-memory mandate/catalog/audit/clock so each FR-ID is verified
independently without mutating the real mandate.yaml or audit log on disk.
"""

from pathlib import Path

import pytest

from interceptor.risk_manager import RiskManager

PRODUCTS = [
    {"sku": "RICE-BASMATI-1KG", "name": "Basmati Rice 1kg", "price_inr": 180, "category": "Staples"},
    {"sku": "MILK-TONED-1L", "name": "Toned Milk 1L", "price_inr": 58, "category": "Dairy"},
    {"sku": "GIFT-CARD-500", "name": "Gift Card 500", "price_inr": 500, "category": "Gift Cards"},
    {"sku": "GC-AMAZON-500", "name": "Amazon Gift Card ₹500", "price_inr": 500, "category": "Gift Cards"},
]


def make_mandate(**overrides):
    mandate = {
        "mandate_id": "MAND-TEST-1",
        "user_id": "user-test",
        "status": "active",
        "limits": {
            "max_per_transaction": 1000,
            "max_cumulative": 5000,
            "cumulative_window_hours": 24,
            "max_attempts_per_minute": 5,
        },
        "scope": {
            "allowed_mcc": ["5411"],
            "allowed_merchants": ["amart-grocers-001"],
            "blocked_categories": ["Gift Cards", "Alcohol"],
        },
    }
    mandate.update(overrides)
    return mandate


def make_catalog(products=None):
    return {
        "merchant_id": "amart-grocers-001",
        "merchant_name": "Amart Grocers",
        "mcc": "5411",
        "products": products if products is not None else PRODUCTS,
    }


def make_tool_call(**arg_overrides):
    args = {
        "merchant_id": "amart-grocers-001",
        "items": [{"sku": "RICE-BASMATI-1KG", "qty": 1, "name": "Basmati Rice 1kg"}],
        "amount_inr": 180,
    }
    args.update(arg_overrides)
    return {"tool": "create_payment_intent", "args": args}


class StaticClock:
    """Mutable clock for velocity/cumulative-window tests."""

    def __init__(self, start):
        self.current = start

    def advance(self, seconds=0, hours=0):
        from datetime import timedelta

        self.current = self.current + timedelta(seconds=seconds, hours=hours)

    def __call__(self):
        return self.current


@pytest.fixture
def env():
    """Return a factory + shared containers for constructing RiskManagers."""
    from datetime import datetime, timezone

    state = {
        "mandate": make_mandate(),
        "catalog": make_catalog(),
        "audit": [],
        "clock": StaticClock(datetime(2026, 8, 29, 12, 0, 0)),
    }

    def build():
        def loader():
            return state["mandate"]

        def writer(m):
            state["mandate"] = m

        def cat():
            return state["catalog"]

        def append(entry):
            state["audit"].append(entry)

        return RiskManager(
            mandate_loader=loader,
            mandate_writer=writer,
            catalog_loader=cat,
            audit_append=append,
            now=state["clock"],
        )

    return state, build