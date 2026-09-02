from scripts.seed_demo import PRODUCTS


def test_seed_has_one_hundred_valid_products():
    assert len(PRODUCTS) == 100
    codes = [row[0] for row in PRODUCTS]
    assert len(set(codes)) == 100, "los códigos deben ser únicos"
    for code, name, category, cost, price, stock, description in PRODUCTS:
        assert code.strip() and name.strip() and category.strip() and description.strip()
        assert cost > 0 and price > cost, f"{name}: el precio debe superar al costo"
        assert stock >= 0


def test_seed_covers_varied_cases():
    stocks = [row[5] for row in PRODUCTS]
    codes = [row[0] for row in PRODUCTS]
    categories = {row[2] for row in PRODUCTS}
    assert 0 in stocks, "debe haber productos agotados"
    assert any(0 < stock <= 3 for stock in stocks), "debe haber productos con pocas existencias"
    assert any(not code.isdigit() for code in codes), "debe haber códigos internos alfanuméricos"
    assert any(len(code) == 13 and code.isdigit() for code in codes), "debe haber códigos de barras EAN-13"
    assert len(categories) >= 8
