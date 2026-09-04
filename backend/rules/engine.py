import datetime
from sqlalchemy.orm import Session
from backend.database.models import Transaction, PurchaseOrder, Shipment, GoodsReceipt, Invoice, Payment

from backend.rules.policy import get_accounting_policy

CUTOFF_DATE = datetime.datetime(2026, 12, 31, 23, 59, 59)
WINDOW_DAYS = 7

def is_within_cutoff_window(tx: Transaction, cutoff_date: datetime.datetime = CUTOFF_DATE, window_days: int = WINDOW_DAYS) -> bool:
    """Checks if the transaction date or posting date is within the configured window (default ±7 days)."""
    delta = datetime.timedelta(days=window_days)
    start_window = cutoff_date - delta
    end_window = cutoff_date + delta

    in_tx_window = start_window <= tx.transaction_date <= end_window
    in_post_window = start_window <= tx.posting_date <= end_window

    return in_tx_window or in_post_window

def evaluate_transaction_rules(db: Session, tx_id: str, cutoff_date: datetime.datetime = CUTOFF_DATE, window_days: int = WINDOW_DAYS) -> dict:
    """
    Applies deterministic financial rules to a transaction.
    Returns a dict with:
      - requires_investigation: bool
      - classification: str
      - reason: str
      - rules_triggered: list[str]
      - economic_event_date: str | None (ISO format)
      - evidence_ids: list[str]
      - policy_applied: str
    """
    tx = db.query(Transaction).filter(Transaction.transaction_id == tx_id).first()
    if not tx:
        return {
            "requires_investigation": False,
            "classification": "DATA_QUALITY_EXCEPTION",
            "reason": "Transaction not found in database",
            "rules_triggered": ["TXN_NOT_FOUND"],
            "economic_event_date": None,
            "evidence_ids": [],
            "policy_applied": "POLICY-UNKNOWN-ESCALATION"
        }

    policy = get_accounting_policy(tx.transaction_type)
    policy_name = policy.name
    rules_triggered = []

    # Fetch related records
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.transaction_id == tx_id).all()
    invoices = db.query(Invoice).filter(Invoice.transaction_id == tx_id).all()
    payments = db.query(Payment).filter(Payment.transaction_id == tx_id).all()

    # Rule 0: Data quality checks (run before timing logic — corruption is orthogonal to cutoff timing)
    if tx.amount <= 0:
        rules_triggered.append("INVALID_AMOUNT")
        return {
            "requires_investigation": False,
            "classification": "DATA_QUALITY_EXCEPTION",
            "reason": f"Transaction amount ({tx.amount}) is zero or negative — invalid financial record.",
            "rules_triggered": rules_triggered,
            "economic_event_date": None,
            "evidence_ids": [],
            "policy_applied": policy_name
        }

    if invoices:
        for inv in invoices:
            mismatch_threshold = max(0.01 * tx.amount, 1.0)
            if abs(inv.amount - tx.amount) > mismatch_threshold:
                rules_triggered.append("INVOICE_AMOUNT_MISMATCH")
                return {
                    "requires_investigation": False,
                    "classification": "DATA_QUALITY_EXCEPTION",
                    "reason": f"Invoice amount ({inv.amount}) does not reconcile with transaction amount ({tx.amount}) — data entry error suspected.",
                    "rules_triggered": rules_triggered,
                    "economic_event_date": None,
                    "evidence_ids": [inv.invoice_id],
                    "policy_applied": policy_name
                }

    # Rule 1: Validate window
    if not is_within_cutoff_window(tx, cutoff_date, window_days):
        is_before = tx.transaction_date <= cutoff_date
        classification = "BEFORE_CUTOFF" if is_before else "AFTER_CUTOFF"
        return {
            "requires_investigation": False,
            "classification": classification,
            "reason": f"Transaction is outside the configured cutoff window ({window_days} days).",
            "rules_triggered": ["OUTSIDE_CUTOFF_WINDOW"],
            "economic_event_date": tx.transaction_date.isoformat(),
            "evidence_ids": [inv.invoice_id for inv in invoices],
            "policy_applied": policy_name
        }

    rules_triggered.append("WITHIN_CUTOFF_WINDOW")

    # Rule 2: Basic invoice check
    if not invoices:
        rules_triggered.append("MISSING_INVOICE")
        return {
            "requires_investigation": True,
            "classification": "REQUIRES_AI_INVESTIGATION",
            "reason": "Invoice record is missing for this transaction.",
            "rules_triggered": rules_triggered,
            "economic_event_date": None,
            "evidence_ids": [],
            "policy_applied": policy_name
        }

    invoice_dates = [inv.invoice_date for inv in invoices]
    all_invoices_before = all(d <= cutoff_date for d in invoice_dates)
    all_invoices_after = all(d > cutoff_date for d in invoice_dates)

    if tx.transaction_type == "goods_purchase":
        grns = []
        shipments = []
        for po in pos:
            grns.extend(db.query(GoodsReceipt).filter(GoodsReceipt.po_id == po.po_id).all())
            shipments.extend(db.query(Shipment).filter(Shipment.po_id == po.po_id).all())

        if not grns and not shipments:
            rules_triggered.append("MISSING_DELIVERY_EVIDENCE")
            return {
                "requires_investigation": True,
                "classification": "REQUIRES_AI_INVESTIGATION",
                "reason": "Purchase orders exist, but there is no Goods Receipt or Shipment record in the system.",
                "rules_triggered": rules_triggered,
                "economic_event_date": None,
                "evidence_ids": [inv.invoice_id for inv in invoices],
                "policy_applied": policy_name
            }

        if not grns:
            rules_triggered.append("MISSING_GOODS_RECEIPT")
            return {
                "requires_investigation": True,
                "classification": "REQUIRES_AI_INVESTIGATION",
                "reason": "Shipment exists but no local Goods Receipt (GRN) has been recorded.",
                "rules_triggered": rules_triggered,
                "economic_event_date": None,
                "evidence_ids": [s.shipment_id for s in shipments] + [inv.invoice_id for inv in invoices],
                "policy_applied": policy_name
            }

        grn_dates = [grn.receipt_date for grn in grns]
        all_grn_before = all(d <= cutoff_date for d in grn_dates)
        all_grn_after = all(d > cutoff_date for d in grn_dates)

        shipment_dates = [ship.delivery_date for ship in shipments if ship.delivery_date]
        all_ship_before = all(d <= cutoff_date for d in shipment_dates) if shipment_dates else True
        all_ship_after = all(d > cutoff_date for d in shipment_dates) if shipment_dates else True

        has_date_contradiction = False
        for grn in grns:
            for ship in shipments:
                if ship.delivery_date and grn.receipt_date <= cutoff_date and ship.delivery_date > cutoff_date:
                    has_date_contradiction = True
                    break

        if has_date_contradiction:
            rules_triggered.append("CONTRADICTORY_DATES_DETECTED")
            return {
                "requires_investigation": True,
                "classification": "REQUIRES_AI_INVESTIGATION",
                "reason": "Contradictory evidence: internal Goods Receipt dates precede period-end, but external carrier tracking delivery logs indicate receipt after period-end.",
                "rules_triggered": rules_triggered,
                "economic_event_date": None,
                "evidence_ids": [g.grn_id for g in grns] + [s.shipment_id for s in shipments],
                "policy_applied": policy_name
            }

        combined_evidence_ids = [g.grn_id for g in grns] + [s.shipment_id for s in shipments] + [inv.invoice_id for inv in invoices]

        if all_grn_before and all_invoices_before and all_ship_before:
            rules_triggered.append("DETERMINISTIC_CLEAR_BEFORE")
            return {
                "requires_investigation": False,
                "classification": "CLEAR_BEFORE_CUTOFF",
                "reason": "Deterministic resolution: all delivery logs, invoice dates, and shipping confirmation dates are aligned before cutoff.",
                "rules_triggered": rules_triggered,
                "economic_event_date": grn_dates[0].isoformat(),
                "evidence_ids": combined_evidence_ids,
                "policy_applied": policy_name
            }

        if all_grn_after and all_invoices_after and all_ship_after:
            rules_triggered.append("DETERMINISTIC_CLEAR_AFTER")
            return {
                "requires_investigation": False,
                "classification": "CLEAR_AFTER_CUTOFF",
                "reason": "Deterministic resolution: all delivery logs, invoice dates, and shipping confirmation dates are aligned after cutoff.",
                "rules_triggered": rules_triggered,
                "economic_event_date": grn_dates[0].isoformat(),
                "evidence_ids": combined_evidence_ids,
                "policy_applied": policy_name
            }

        rules_triggered.append("AMBIGUOUS_DATES_CROSS_CUTOFF")
        return {
            "requires_investigation": True,
            "classification": "REQUIRES_AI_INVESTIGATION",
            "reason": "Audit dates cross the cutoff boundary: invoice and delivery dates are in different periods.",
            "rules_triggered": rules_triggered,
            "economic_event_date": None,
            "evidence_ids": combined_evidence_ids,
            "policy_applied": policy_name
        }

    rules_triggered.append("COMPLEX_TRANSACTION_TYPE")
    return {
        "requires_investigation": True,
        "classification": "REQUIRES_AI_INVESTIGATION",
        "reason": f"Transaction type {tx.transaction_type} requires verification of contract terms or service logs according to policy {policy_name}.",
        "rules_triggered": rules_triggered,
        "economic_event_date": None,
        "evidence_ids": [inv.invoice_id for inv in invoices],
        "policy_applied": policy_name
    }