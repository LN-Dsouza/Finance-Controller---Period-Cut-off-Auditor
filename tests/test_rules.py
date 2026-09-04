from backend.rules.engine import evaluate_transaction_rules, is_within_cutoff_window
from tests.conftest import add_goods_case


def test_cutoff_window_includes_posting_near_year_end(db):
    tx = add_goods_case(
        db, "TXN-WIN",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    assert is_within_cutoff_window(tx) is True


def test_clear_before_cutoff(db):
    add_goods_case(
        db, "TXN-BEFORE",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    result = evaluate_transaction_rules(db, "TXN-BEFORE")
    assert result["requires_investigation"] is False
    assert result["classification"] == "CLEAR_BEFORE_CUTOFF"


def test_clear_after_cutoff(db):
    add_goods_case(
        db, "TXN-AFTER",
        tx_date="2027-01-02",
        posting_date="2027-01-03",
        invoice_date="2027-01-04",
        grn_date="2027-01-03",
        ship_date="2027-01-02",
        delivery_date="2027-01-03",
        ledger_period="January 2027",
    )
    result = evaluate_transaction_rules(db, "TXN-AFTER")
    assert result["requires_investigation"] is False
    assert result["classification"] == "CLEAR_AFTER_CUTOFF"


def test_missing_grn_requires_investigation(db):
    add_goods_case(
        db, "TXN-MISS",
        tx_date="2026-12-28",
        posting_date="2026-12-29",
        invoice_date="2026-12-30",
        grn_date=None,
        ship_date="2026-12-27",
        delivery_date=None,
    )
    result = evaluate_transaction_rules(db, "TXN-MISS")
    assert result["requires_investigation"] is True
    assert "MISSING_GOODS_RECEIPT" in result["rules_triggered"]


def test_contradiction_requires_investigation(db):
    add_goods_case(
        db, "TXN-CONTRA",
        tx_date="2026-12-20",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-27",
        delivery_date="2027-01-03",
    )
    result = evaluate_transaction_rules(db, "TXN-CONTRA")
    assert result["requires_investigation"] is True
    assert "CONTRADICTORY_DATES_DETECTED" in result["rules_triggered"]


def test_invoice_after_receipt_is_ambiguous(db):
    add_goods_case(
        db, "TXN-CROSS",
        tx_date="2026-12-20",
        posting_date="2027-01-02",
        invoice_date="2027-01-02",
        grn_date="2026-12-30",
        ship_date="2026-12-28",
        delivery_date="2026-12-30",
    )
    result = evaluate_transaction_rules(db, "TXN-CROSS")
    assert result["requires_investigation"] is True
