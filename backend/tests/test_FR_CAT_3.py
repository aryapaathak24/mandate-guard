from catalog.catalog import load_catalog


def test_FR_CAT_3_every_product_has_category(env):
    catalog = load_catalog()

    assert catalog["products"], "catalog must contain at least one product"

    for product in catalog["products"]:
        category = product.get("category")
        assert category, f"product SKU '{product.get('sku')}' is missing a category"
        assert isinstance(category, str) and category.strip()