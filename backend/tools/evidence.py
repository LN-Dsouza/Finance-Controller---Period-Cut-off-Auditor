from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database.models import (
    Transaction, PurchaseOrder, Shipment, GoodsReceipt, Invoice,
    Payment, ServiceRecord, Contract, Evidence
)
from backend.privacy.gateway import PrivacyGateway
from backend.retrieval.vector_store import search_semantic_evidence

# Standard instance of PrivacyGateway for sanitizing tool outputs
privacy_gw = PrivacyGateway()

def record_provenance(tool_name: str, record_id: str, source_type: str, data: dict) -> dict:
    """Helper to attach audit provenance to any retrieved evidence."""
    return {
        "evidence_id": f"EV-{tool_name.upper()}-{record_id}",
        "source_type": source_type,
        "source_record": record_id,
        "data": data,
        "reliability": "HIGH"
    }

def get_transaction(db: Session, transaction_id: str) -> dict:
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not tx:
        return {"error": f"Transaction {transaction_id} not found."}
    
    minimized = privacy_gw.minimize_transaction(tx)
    return record_provenance("get_transaction", transaction_id, "transaction", minimized)

def get_related_invoice(db: Session, transaction_id: str) -> dict:
    inv = db.query(Invoice).filter(Invoice.transaction_id == transaction_id).first()
    if not inv:
        return {"error": f"Invoice for transaction {transaction_id} not found."}
    
    minimized = privacy_gw.minimize_invoice(inv)
    return record_provenance("get_invoice", inv.invoice_id, "invoice", minimized)

def get_purchase_order(db: Session, transaction_id: str) -> dict:
    po = db.query(PurchaseOrder).filter(PurchaseOrder.transaction_id == transaction_id).first()
    if not po:
        return {"error": f"Purchase Order for transaction {transaction_id} not found."}
    
    minimized = privacy_gw.minimize_purchase_order(po)
    return record_provenance("get_purchase_order", po.po_id, "purchase_order", minimized)

def get_goods_receipt(db: Session, po_id: str) -> dict:
    grn = db.query(GoodsReceipt).filter(GoodsReceipt.po_id == po_id).first()
    if not grn:
        return {"error": f"Goods Receipt for PO {po_id} not found."}
    
    minimized = privacy_gw.minimize_goods_receipt(grn)
    return record_provenance("get_goods_receipt", grn.grn_id, "goods_receipt", minimized)

def get_shipping_record(db: Session, po_id: str) -> dict:
    ship = db.query(Shipment).filter(Shipment.po_id == po_id).first()
    if not ship:
        return {"error": f"Shipment for PO {po_id} not found."}
    
    minimized = privacy_gw.minimize_shipment(ship)
    return record_provenance("get_shipping_record", ship.shipment_id, "shipment", minimized)

def get_payment(db: Session, transaction_id: str) -> dict:
    pay = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
    if not pay:
        return {"error": f"Payment for transaction {transaction_id} not found."}
    
    minimized = privacy_gw.minimize_payment(pay)
    return record_provenance("get_payment", pay.payment_id, "payment", minimized)

def get_service_record(db: Session, transaction_id: str) -> dict:
    srv = db.query(ServiceRecord).filter(ServiceRecord.transaction_id == transaction_id).first()
    if not srv:
        return {"error": f"Service Record for transaction {transaction_id} not found."}
    
    data = {
        "service_id": srv.service_id,
        "transaction_id": srv.transaction_id,
        "service_start": srv.service_start.isoformat(),
        "service_end": srv.service_end.isoformat(),
        "completion_status": srv.completion_status
    }
    return record_provenance("get_service_record", srv.service_id, "service_record", data)

def get_contract(db: Session, transaction_id: str) -> dict:
    contract = db.query(Contract).filter(Contract.transaction_id == transaction_id).first()
    if not contract:
        return {"error": f"Contract for transaction {transaction_id} not found."}
    
    data = {
        "contract_id": contract.contract_id,
        "transaction_id": contract.transaction_id,
        "effective_date": contract.effective_date.isoformat(),
        "service_period": contract.service_period,
        "terms": privacy_gw.redact_text(contract.terms)
    }
    return record_provenance("get_contract", contract.contract_id, "contract", data)

def check_duplicate(db: Session, transaction_id: str) -> dict:
    """Scans for potential duplicate transactions with identical amount/type/parties."""
    current = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not current:
        return {"error": "Current transaction not found."}
        
    duplicates = db.query(Transaction).filter(
        Transaction.transaction_id != transaction_id,
        Transaction.amount == current.amount,
        Transaction.transaction_type == current.transaction_type,
        Transaction.vendor_id == current.vendor_id,
        Transaction.customer_id == current.customer_id
    ).all()
    
    res = [privacy_gw.minimize_transaction(d) for d in duplicates]
    return {
        "tool": "check_duplicate",
        "duplicate_count": len(res),
        "duplicates": res
    }

def check_related_transactions(db: Session, transaction_id: str) -> dict:
    """Gets other transactions for the same vendor/customer within a short period."""
    current = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not current:
        return {"error": "Current transaction not found."}
        
    related = db.query(Transaction).filter(
        Transaction.transaction_id != transaction_id,
        (Transaction.vendor_id == current.vendor_id) | (Transaction.customer_id == current.customer_id)
    ).all()
    
    res = [privacy_gw.minimize_transaction(r) for r in related]
    return {
        "tool": "check_related_transactions",
        "related_count": len(res),
        "related": res
    }

def search_evidence(db: Session, query: str, transaction_id: str) -> dict:
    """Queries semantic evidence and returns redacted results matching transaction_id."""
    raw_results = search_semantic_evidence(db, query, limit=5)
    
    # Filter for transaction_id and redact PII
    sanitized = []
    for r in raw_results:
        if r["transaction_id"] == transaction_id:
            r["content"] = privacy_gw.redact_text(r["content"])
            sanitized.append(r)
            
    return {
        "tool": "search_evidence",
        "query": query,
        "results": sanitized
    }
