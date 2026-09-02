from decimal import Decimal

import pytest

from utils.formatters import format_price, parse_int, parse_money, to_decimal


def test_format_price_uses_dots_for_thousands():
    assert format_price(Decimal("1234567")) == "1.234.567"


def test_format_price_with_decimals_uses_comma():
    assert format_price(Decimal("1500.5"), decimals=2) == "1.500,50"


def test_format_price_rounds_half_up():
    assert format_price(Decimal("2.5")) == "3"


def test_format_price_accepts_text_none_and_garbage():
    assert format_price("1.500") == "1.500"
    assert format_price(None) == "0"
    assert format_price("basura") == "0"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.500", "1500"),
        ("1.500,50", "1500.50"),
        ("$ 2.000", "2000"),
        ("1500", "1500"),
        ("0", "0"),
    ],
)
def test_parse_money(text, expected):
    assert parse_money(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "   ", "abc", "-5", "1,2,3"])
def test_parse_money_rejects_invalid(text):
    with pytest.raises(ValueError):
        parse_money(text)


def test_parse_int_accepts_thousands_separator():
    assert parse_int("12") == 12
    assert parse_int("1.000") == 1000


def test_parse_int_enforces_minimum():
    with pytest.raises(ValueError):
        parse_int("0", minimum=1)


def test_parse_int_rejects_text():
    with pytest.raises(ValueError):
        parse_int("doce")


def test_to_decimal_from_float_is_exact_text():
    assert to_decimal(0.1) == Decimal("0.1")
