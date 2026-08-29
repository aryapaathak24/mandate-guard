"""Mandate loader/writer module.

Flat-file (YAML) persistence for the spending mandate. This is the prototype
backing store; the schema mirrors SRS section 6.1 so it can later be swapped
for Postgres/Supabase without changing the interface.
"""

from datetime import datetime, timezone
from pathlib import Path

import yaml

MANDATE_DIR = Path(__file__).parent
MANDATE_PATH = MANDATE_DIR / "mandate.yaml"


def load_mandate(path: Path = MANDATE_PATH) -> dict:
    """Read and parse the mandate file (re-read every call — FR-MAN-9)."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_mandate(mandate: dict, path: Path = MANDATE_PATH) -> None:
    """Persist the mandate back to YAML."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(mandate, f, sort_keys=False, default_flow_style=False)


def revoke(mandate: dict) -> dict:
    """Set status to 'revoked' and record revoked_at (FR-MAN-7, FR-MAN-8)."""
    mandate["status"] = "revoked"
    mandate["revoked_at"] = datetime.now(timezone.utc).isoformat()
    return mandate


def is_active(mandate: dict) -> bool:
    return mandate.get("status") == "active"