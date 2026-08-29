import json
from pathlib import Path

CATALOG_DIR = Path(__file__).parent


def load_catalog() -> dict:
    with open(CATALOG_DIR / "products.json", encoding="utf-8") as f:
        return json.load(f)