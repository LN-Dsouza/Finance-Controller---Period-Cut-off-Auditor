import os
import json
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from backend.privacy.gateway import PrivacyGateway

from backend.database.connection import get_db, init_db
from backend.database.models import (
    Transaction, PurchaseOrder, Shipment, GoodsReceipt, Invoice,
    Payment, ServiceRecord, Contract, Evidence, Investigation,
    HumanReview, AuditLog
)
from backend.evaluation.pipeline import run_evaluation_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AI Finance Controller - Period-End Cut-Off Auditor", lifespan=lifespan)

# Enable CORS for frontend dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo / hackathon deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas for request validation
privacy_gw = PrivacyGateway()
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESULTS_PATH = os.path.join(DATA_DIR, "evaluation_results.json")
ALLOWED_REVIEW_DECISIONS = {"APPROVE", "REJECT", "REQUEST_MORE_EVIDENCE"}

class ReviewSubmit(BaseModel):
    reviewer: str = Field(min_length=1)
    decision: str
    comment: Optional[str] = ""

class AuditRunRequest(BaseModel):
    cutoff_date: Optional[str] = "2026-12-31 23:59:59"
    window_days: Optional[int] = 7

@app.post("/api/audit/run")
def run_audit(payload: Optional[AuditRunRequest] = None):
    """Triggers the full period-end cut-off audit loop across all transactions."""
    try:
        cutoff_date = payload.cutoff_date if payload and payload.cutoff_date else "2026-12-31 23:59:59"
        window_days = payload.window_days if payload and payload.window_days is not None else 7
        metrics = run_evaluation_pipeline(cutoff_date=cutoff_date, window_days=window_days)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed")
def seed_dataset():
    """Resets and seeds the database with the full 75-transaction synthetic dataset."""
    try:
        from backend.database.seed import generate_synthetic_data
        generate_synthetic_data()
        return {"status": "SUCCESS", "message": "Database successfully reset and seeded with 75 transactions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/policies")
def list_policies():
    """Returns all active configurable accounting policies."""
    from backend.rules.policy import list_all_policies
    return list_all_policies()

@app.get("/api/langsmith/status")
def get_langsmith_status():
    """Returns LangSmith tracing status, project, and configuration."""
    tracing = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false")).lower() in ("1", "true", "yes")
    api_key_set = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
    project = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "ai-finance-controller"))
    return {
        "tracing_enabled": tracing,
        "api_key_configured": api_key_set,
        "project": project,
        "active": tracing and api_key_set,
        "endpoint": os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    }

@app.get("/api/audit/runs")
def list_audit_runs(db: Session = Depends(get_db)):
    """Lists distinct investigation run identifiers."""
    rows = db.query(AuditLog.run_id, AuditLog.timestamp).order_by(AuditLog.timestamp.desc()).all()
    seen = []
    used = set()
    for run_id, ts in rows:
        if run_id in used:
            continue
        used.add(run_id)
        seen.append({"run_id": run_id, "timestamp": ts.isoformat() if ts else None})
    return seen

@app.get("/api/metrics")
def get_metrics():
    """Returns the latest evaluation performance and safety metrics."""
    if not os.path.exists(RESULTS_PATH):
        raise HTTPException(status_code=404, detail="No metrics available. POST /api/audit/run first.")
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)

@app.get("/api/transactions")
def list_transactions(db: Session = Depends(get_db)):
    """Lists all transactions in the ledger with their type and audit statuses."""
    txs = db.query(Transaction).all()
    res = []
    for t in txs:
        # Check if an investigation exists
        inv = db.query(Investigation).filter(Investigation.transaction_id == t.transaction_id).first()
        res.append({
            "transaction_id": t.transaction_id,
            "transaction_type": t.transaction_type,
            "amount": t.amount,
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "posting_date": t.posting_date.isoformat(),
            "ledger_period": t.ledger_period,
            "vendor_id": t.vendor_id,
            "customer_id": t.customer_id,
            "status": t.status,
            "classification": inv.final_classification if inv else "UNAUDITED",
            "confidence": inv.confidence if inv else 0.0,
            "human_review_required": inv.human_review_required if inv else False
        })
    return res

@app.get("/api/transactions/{id}")
def get_transaction_detail(id: str, db: Session = Depends(get_db)):
    """Retrieves full details of a transaction, including purchase logs and payments."""
    t = db.query(Transaction).filter(Transaction.transaction_id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.transaction_id == id).all()
    invoices = db.query(Invoice).filter(Invoice.transaction_id == id).all()
    payments = db.query(Payment).filter(Payment.transaction_id == id).all()
    services = db.query(ServiceRecord).filter(ServiceRecord.transaction_id == id).all()
    contracts = db.query(Contract).filter(Contract.transaction_id == id).all()
    evidences = db.query(Evidence).filter(Evidence.transaction_id == id).all()
    investigation = db.query(Investigation).filter(Investigation.transaction_id == id).first()
    reviews = db.query(HumanReview).filter(HumanReview.transaction_id == id).all()

    # Reconstruct timeline of events
    timeline = []
    timeline.append({"event": "Transaction Created", "date": t.transaction_date.isoformat(), "source": "General Ledger"})
    timeline.append({"event": "Transaction Posted", "date": t.posting_date.isoformat(), "source": "General Ledger"})
    
    for po in pos:
        timeline.append({"event": f"PO Created ({po.po_id})", "date": po.po_date.isoformat(), "source": "Purchasing"})
        # Shipments
        ships = db.query(Shipment).filter(Shipment.po_id == po.po_id).all()
        for s in ships:
            timeline.append({"event": f"Goods Shipped ({s.shipment_id})", "date": s.ship_date.isoformat(), "source": "Logistics"})
            if s.delivery_date:
                timeline.append({"event": f"Goods Shipped Delivery Confirmed ({s.shipment_id})", "date": s.delivery_date.isoformat(), "source": "Carrier Tracker"})
        # GRNs
        grns = db.query(GoodsReceipt).filter(GoodsReceipt.po_id == po.po_id).all()
        for g in grns:
            timeline.append({"event": f"Goods Receipt Logged ({g.grn_id})", "date": g.receipt_date.isoformat(), "source": "Warehouse Inventory"})

    for inv in invoices:
        timeline.append({"event": f"Invoice Received ({inv.invoice_id})", "date": inv.invoice_date.isoformat(), "source": "AP Invoicing"})
        
    for pay in payments:
        timeline.append({"event": f"Payment Processed ({pay.payment_id})", "date": pay.payment_date.isoformat(), "source": "Treasury Settlement"})

    for srv in services:
        timeline.append({"event": f"Service Started", "date": srv.service_start.isoformat(), "source": "Service Operations"})
        timeline.append({"event": f"Service Completed ({srv.completion_status})", "date": srv.service_end.isoformat(), "source": "Service Operations"})

    # Sort timeline by date
    timeline.sort(key=lambda x: x["date"])

    return {
        "transaction": {
            "transaction_id": t.transaction_id,
            "transaction_type": t.transaction_type,
            "amount": t.amount,
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "posting_date": t.posting_date.isoformat(),
            "ledger_period": t.ledger_period,
            "vendor_id": t.vendor_id,
            "customer_id": t.customer_id,
            "status": t.status,
        },
        "purchase_orders": [{"po_id": po.po_id, "amount": po.amount, "po_date": po.po_date.isoformat(), "description": po.description} for po in pos],
        "invoices": [{"invoice_id": inv.invoice_id, "amount": inv.amount, "invoice_date": inv.invoice_date.isoformat()} for inv in invoices],
        "payments": [{"payment_id": pay.payment_id, "amount": pay.amount, "payment_date": pay.payment_date.isoformat()} for pay in payments],
        "timeline": timeline,
        "evidence": [{
            "evidence_id": ev.evidence_id,
            "source_type": ev.source_type,
            "content": privacy_gw.redact_text(ev.content),
            "relevant_date": ev.relevant_date.isoformat() if ev.relevant_date else None,
            "reliability": ev.reliability
        } for ev in evidences],
        "investigation": {
            "investigation_id": investigation.investigation_id,
            "run_id": investigation.run_id,
            "status": investigation.status,
            "cutoff_date": investigation.cutoff_date.isoformat() if investigation.cutoff_date else None,
            "economic_event_date": investigation.economic_event_date.isoformat() if investigation.economic_event_date else None,
            "classification": investigation.final_classification,
            "confidence": investigation.confidence,
            "reasoning_summary": investigation.reasoning_summary,
            "policy_applied": investigation.policy_applied,
            "known_facts": investigation.known_facts or [],
            "missing_evidence": investigation.missing_evidence or [],
            "contradictions": investigation.contradictions or [],
            "recommended_action": investigation.recommended_action,
            "human_review_required": investigation.human_review_required,
            "steps": investigation.steps or []
        } if investigation else None,
        "reviews": [{"reviewer": r.reviewer, "timestamp": r.timestamp.isoformat(), "decision": r.human_decision, "comment": r.comment} for r in reviews]
    }

@app.get("/api/exceptions")
def list_exceptions(db: Session = Depends(get_db)):
    """Exposes transactions flagged as UNRESOLVED or POTENTIAL_MISSTATEMENT for human queue."""
    invs = db.query(Investigation).filter(Investigation.final_classification.in_(["UNRESOLVED", "POTENTIAL_MISSTATEMENT", "DATA_QUALITY_EXCEPTION"])).all()
    res = []
    for inv in invs:
        t = db.query(Transaction).filter(Transaction.transaction_id == inv.transaction_id).first()
        if not t:
            continue
        ev_count = db.query(Evidence).filter(Evidence.transaction_id == t.transaction_id).count()
        res.append({
            "transaction_id": t.transaction_id,
            "transaction_type": t.transaction_type,
            "amount": t.amount,
            "currency": t.currency,
            "ledger_period": t.ledger_period,
            "vendor_id": t.vendor_id,
            "cutoff_date": inv.cutoff_date.isoformat() if inv.cutoff_date else None,
            "classification": inv.final_classification,
            "confidence": inv.confidence,
            "evidence_count": ev_count,
            "missing_evidence": inv.missing_evidence or [],
            "contradictions": inv.contradictions or [],
            "status": t.status,
            "human_review_required": inv.human_review_required,
            "policy_applied": inv.policy_applied
        })
    return res

@app.post("/api/reviews/{id}")
def submit_human_review(id: str, review: ReviewSubmit, db: Session = Depends(get_db)):
    """Allows a human reviewer to resolve a flagged transaction (APPROVE, REJECT, REQUEST_MORE_EVIDENCE)."""
    tx = db.query(Transaction).filter(Transaction.transaction_id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    inv = db.query(Investigation).filter(Investigation.transaction_id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="No AI investigation exists for this transaction")
    if review.decision not in ALLOWED_REVIEW_DECISIONS:
        raise HTTPException(status_code=400, detail="decision must be APPROVE, REJECT, or REQUEST_MORE_EVIDENCE")

    # Save Review record
    db_rev = HumanReview(
        review_id=f"REV-{int(datetime.datetime.now(datetime.UTC).timestamp())}",
        transaction_id=id,
        reviewer=review.reviewer,
        original_classification=inv.final_classification,
        human_decision=review.decision,
        comment=review.comment
    )
    db.add(db_rev)

    # Update ledger status based on reviewer input
    if review.decision == "APPROVE":
        tx.status = "AUDITED"
        inv.human_review_required = False
    elif review.decision == "REJECT":
        tx.status = "REJECTED"
        inv.human_review_required = False
    else:
        # Request more evidence - keep status pending
        tx.status = "PENDING"
        inv.human_review_required = True

    # Update Audit Log with human interaction details
    audit_log = db.query(AuditLog).filter(AuditLog.transaction_id == id).first()
    if audit_log:
        audit_log.human_decision = review.decision
        audit_log.reviewer = review.reviewer
        
    db.commit()
    return {"status": "SUCCESS", "message": f"Review saved. Decision: {review.decision}"}

@app.get("/api/investigations/{id}")
def get_investigation(id: str, db: Session = Depends(get_db)):
    """Returns the structured investigation decision for a transaction."""
    inv = db.query(Investigation).filter(
        (Investigation.investigation_id == id) | (Investigation.transaction_id == id)
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "investigation_id": inv.investigation_id,
        "transaction_id": inv.transaction_id,
        "run_id": inv.run_id,
        "status": inv.status,
        "cutoff_date": inv.cutoff_date.isoformat() if inv.cutoff_date else None,
        "economic_event_date": inv.economic_event_date.isoformat() if inv.economic_event_date else None,
        "classification": inv.final_classification,
        "confidence": inv.confidence,
        "reasoning_summary": inv.reasoning_summary,
        "known_facts": inv.known_facts or [],
        "missing_evidence": inv.missing_evidence or [],
        "contradictions": inv.contradictions or [],
        "recommended_action": inv.recommended_action,
        "human_review_required": inv.human_review_required,
        "policy_applied": inv.policy_applied,
        "steps": inv.steps or [],
    }

@app.get("/api/audit-log/{id}")
def get_audit_log(id: str, db: Session = Depends(get_db)):
    """Retrieves the immutable audit trail log for a transaction."""
    log = db.query(AuditLog).filter(AuditLog.transaction_id == id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {
        "log_id": log.log_id,
        "run_id": log.run_id,
        "transaction_id": log.transaction_id,
        "timestamp": log.timestamp.isoformat(),
        "rules_triggered": log.rules_triggered,
        "tools_called": log.tools_called,
        "evidence_retrieved": log.evidence_retrieved,
        "hypotheses_and_steps": log.hypotheses,
        "verification_results": log.verification_results,
        "classification": log.classification,
        "confidence": log.confidence,
        "recommended_action": log.recommended_action,
        "policy_applied": log.policy_applied,
        "human_decision": log.human_decision,
        "reviewer": log.reviewer
    }

@app.get("/api/audit-log")
def list_audit_logs(db: Session = Depends(get_db)):
    """Lists all available audit trail logs."""
    logs = db.query(AuditLog).all()
    return [
        {
            "log_id": l.log_id,
            "transaction_id": l.transaction_id,
            "timestamp": l.timestamp.isoformat(),
            "classification": l.classification,
            "confidence": l.confidence,
            "policy_applied": l.policy_applied,
            "reviewer": l.reviewer,
            "human_decision": l.human_decision
        } for l in logs
    ]
