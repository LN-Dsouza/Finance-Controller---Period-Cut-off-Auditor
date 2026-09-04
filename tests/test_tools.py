from backend.tools.evidence import get_goods_receipt, get_transaction, check_duplicate
from tests.conftest import add_goods_case


def test_tools_return_provenance_and_minimum_fields(db):
    add_goods_case(
        db, "TXN-TOOL",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    tx = get_transaction(db, "TXN-TOOL")
    assert tx["evidence_id"].startswith("EV-")
    assert tx["source_record"] == "TXN-TOOL"
    assert "data" in tx
    grn = get_goods_receipt(db, "PO-TXN-TOOL")
    assert grn["source_type"] == "goods_receipt"
    assert grn["data"]["received_by"].startswith("[NAME_")


def test_missing_record_is_error_not_hallucinated(db):
    result = get_transaction(db, "TXN-DOES-NOT-EXIST")
    assert "error" in result


def test_duplicate_scan(db):
    add_goods_case(
        db, "TXN-DUP1",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
        amount=5555,
    )
    add_goods_case(
        db, "TXN-DUP2",
        tx_date="2026-12-11",
        posting_date="2026-12-29",
        invoice_date="2026-12-30",
        grn_date="2026-12-29",
        ship_date="2026-12-25",
        delivery_date="2026-12-29",
        amount=5555,
    )
    result = check_duplicate(db, "TXN-DUP1")
    assert result["duplicate_count"] >= 1