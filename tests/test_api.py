import json
import os

from fastapi.testclient import TestClient

from backend.main import ALLOWED_REVIEW_DECISIONS, app
from tests.conftest import add_goods_case
from backend.database.models import Investigation
import datetime


client = TestClient(app)


def test_transactions_list(db):
    add_goods_case(
        db, "TXN-API1",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    res = client.get("/api/transactions")
    assert res.status_code == 200
    ids = [row["transaction_id"] for row in res.json()]
    assert "TXN-API1" in ids


def test_transaction_404():
    res = client.get("/api/transactions/NOPE")
    assert res.status_code == 404


def test_review_validation(db):
    add_goods_case(
        db, "TXN-REV",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    inv = Investigation(
        investigation_id="INV-REV",
        transaction_id="TXN-REV",
        status="ESCALATED",
        run_id="RUN-TEST",
        cutoff_date=datetime.datetime(2026, 12, 31),
        final_classification="UNRESOLVED",
        confidence=0.4,
        reasoning_summary="Missing POD",
        known_facts=["PO exists"],
        missing_evidence=["POD"],
        contradictions=[],
        recommended_action="Request POD",
        human_review_required=True,
        steps=["retrieve_evidence"],
    )
    db.add(inv)
    db.commit()

    bad = client.post("/api/reviews/TXN-REV", json={"reviewer": "A", "decision": "YEET", "comment": "nope"})
    assert bad.status_code == 400
    ok = client.post("/api/reviews/TXN-REV", json={"reviewer": "A", "decision": "APPROVE", "comment": "ok"})
    assert ok.status_code == 200
    assert "APPROVE" in ALLOWED_REVIEW_DECISIONS


def test_metrics_without_run_is_404():
    from backend.main import RESULTS_PATH
    if os.path.exists(RESULTS_PATH):
        # Do not delete shared eval artifacts in the workspace if present;
        # endpoint may return 200 in a seeded workspace.
        res = client.get("/api/metrics")
        assert res.status_code in (200, 404)
    else:
        res = client.get("/api/metrics")
        assert res.status_code == 404


def test_list_policies():
    res = client.get("/api/policies")
    assert res.status_code == 200
    policies = res.json()
    assert len(policies) >= 3
    names = [p["name"] for p in policies]
    assert "POLICY-GOODS-CONTROL-TRANSFER" in names
    assert "POLICY-SERVICE-PERFORMANCE" in names


def test_langsmith_status():
    res = client.get("/api/langsmith/status")
    assert res.status_code == 200
    data = res.json()
    assert "tracing_enabled" in data
    assert "project" in data


def test_exceptions_metadata(db):
    add_goods_case(
        db, "TXN-EX-META",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    inv = Investigation(
        investigation_id="INV-EX-META",
        transaction_id="TXN-EX-META",
        status="ESCALATED",
        run_id="RUN-TEST",
        cutoff_date=datetime.datetime(2026, 12, 31),
        final_classification="UNRESOLVED",
        confidence=0.45,
        reasoning_summary="Missing POD",
        policy_applied="POLICY-GOODS-CONTROL-TRANSFER",
        known_facts=["PO exists"],
        missing_evidence=["Proof of delivery"],
        contradictions=[],
        recommended_action="Request POD",
        human_review_required=True,
        steps=["retrieve_evidence"],
    )
    db.add(inv)
    db.commit()

    res = client.get("/api/exceptions")
    assert res.status_code == 200
    exs = res.json()
    target = next((x for x in exs if x["transaction_id"] == "TXN-EX-META"), None)
    assert target is not None
    assert "cutoff_date" in target
    assert "evidence_count" in target
    assert target["policy_applied"] == "POLICY-GOODS-CONTROL-TRANSFER"
