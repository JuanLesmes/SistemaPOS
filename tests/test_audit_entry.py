import datetime as dt
import json

from model.audit_log import AuditEntry


def make_entry(details):
    return AuditEntry(
        timestamp=dt.datetime(2026, 9, 1, 10, 0), action="modify_product", code="A1", details=details, user=None
    )


def test_changes_from_before_after_json():
    before, after = make_entry(json.dumps({"before": {"price": "1000"}, "after": {"price": "1500"}})).changes()
    assert before == {"price": "1000"}
    assert after == {"price": "1500"}


def test_changes_from_flat_json_go_to_after():
    before, after = make_entry(json.dumps({"category_name": "Bebidas"})).changes()
    assert before == {}
    assert after == {"category_name": "Bebidas"}


def test_changes_from_plain_text_are_shown_raw():
    before, after = make_entry("10 → 15").changes()
    assert before == {}
    assert after == {"detalle": "10 → 15"}


def test_changes_from_empty_details():
    assert make_entry(None).changes() == ({}, {})
