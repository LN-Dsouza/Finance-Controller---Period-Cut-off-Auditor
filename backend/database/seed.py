import os
import json
import datetime
from sqlalchemy.orm import Session
from backend.database.connection import reset_db, SessionLocal
from backend.database.models import (
    Transaction, PurchaseOrder, Shipment, GoodsReceipt, Invoice,
    Payment, ServiceRecord, Contract, Evidence
)
from backend.retrieval.vector_store import add_evidence_record

# Setup seed output directories
os.makedirs("backend/data", exist_ok=True)

CUTOFF_DATE = datetime.datetime(2026, 12, 31, 23, 59, 59)

def parse_date(date_str):
    if not date_str:
        return None
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")

def generate_synthetic_data():
    reset_db()
    db = SessionLocal()
    
    # Ground truth tracking dict
    ground_truth = {}
    
    # Let's generate 60 cases
    cases = []
    
    # -------------------------------------------------------------
    # 1. CATEGORY A: CLEAR BEFORE CUTOFF (15 cases)
    # -------------------------------------------------------------
    for i in range(1, 16):
        tx_id = f"TXN-A{i:02d}"
        po_id = f"PO-A{i:02d}"
        grn_id = f"GRN-A{i:02d}"
        invoice_id = f"INV-A{i:02d}"
        payment_id = f"PAY-A{i:02d}"
        
        amount = 10000 + i * 1500
        tx_date = "2026-12-10"
        posting_date = "2026-12-28"
        receipt_date = "2026-12-28"
        invoice_date = "2026-12-29"
        payment_date = "2027-01-05"
        
        # Save structured case
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-1{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026",
            "po_date": tx_date,
            "ship_date": "2026-12-24",
            "delivery_date": receipt_date,
            "grn_date": receipt_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "FedEx Express",
            "received_by": f"Operator John Doe (+1-555-01{i:02d})",
            "description": f"Standard inventory delivery order {i}.",
            "ground_truth_classification": "BEFORE_CUTOFF",
            "ground_truth_event_date": receipt_date,
            "ground_truth_reason": f"Goods received on {receipt_date}, before cutoff of 2026-12-31.",
            "evidence_text": f"Delivery Confirmation for order {po_id}. Items received at Dock 3 by operator John Doe (+1-555-01{i:02d}) on Dec 28, 2026. Carrier: FedEx, tracking number 99281-A{i:02d}. Routing to bank account 4820-192-{i:02d}."
        })

    # -------------------------------------------------------------
    # 2. CATEGORY B: CLEAR AFTER CUTOFF (15 cases)
    # -------------------------------------------------------------
    for i in range(1, 16):
        tx_id = f"TXN-B{i:02d}"
        po_id = f"PO-B{i:02d}"
        grn_id = f"GRN-B{i:02d}"
        invoice_id = f"INV-B{i:02d}"
        payment_id = f"PAY-B{i:02d}"
        
        amount = 5000 + i * 2000
        tx_date = "2026-12-20"
        posting_date = "2027-01-05"
        receipt_date = "2027-01-04"
        invoice_date = "2027-01-04"
        payment_date = "2027-01-12"
        
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-2{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "January 2027",
            "po_date": tx_date,
            "ship_date": "2026-12-28",
            "delivery_date": receipt_date,
            "grn_date": receipt_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "UPS Ground",
            "received_by": f"Warehouse Clerk Sarah Connor (+1-555-02{i:02d})",
            "description": f"Standard restock shipment {i}.",
            "ground_truth_classification": "AFTER_CUTOFF",
            "ground_truth_event_date": receipt_date,
            "ground_truth_reason": f"Goods received on {receipt_date}, which is after cutoff of 2026-12-31.",
            "evidence_text": f"UPS Shipment details. Shipment {po_id} delivered on Jan 04, 2027. Received by Sarah Connor (+1-555-02{i:02d}) at warehouse entrance B. Account reference #9201-B{i:02d}."
        })

    # -------------------------------------------------------------
    # 3. CATEGORY C: AMBIGUOUS RESOLVABLE BEFORE CUTOFF (10 cases)
    # -------------------------------------------------------------
    # Invoices dated in Jan 2027, but goods receipts / delivery notes prove delivery occurred in late Dec 2026.
    for i in range(1, 11):
        tx_id = f"TXN-C{i:02d}"
        po_id = f"PO-C{i:02d}"
        grn_id = f"GRN-C{i:02d}"
        invoice_id = f"INV-C{i:02d}"
        payment_id = f"PAY-C{i:02d}"
        
        amount = 12000 + i * 3000
        tx_date = "2026-12-15"
        # Mismatch: posting date and ledger period is Jan 2027 (since invoice came late), but delivery was Dec 2026
        posting_date = "2027-01-04"
        receipt_date = f"2026-12-{28+i%3}"  # 28, 29, 30 Dec
        invoice_date = "2027-01-03"
        payment_date = "2027-01-15"
        
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-3{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "January 2027",  # Misstatement risk: posted in Jan, but event in Dec
            "po_date": tx_date,
            "ship_date": "2026-12-25",
            "delivery_date": receipt_date,
            "grn_date": receipt_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "DHL Express",
            "received_by": f"Receiving Manager David Miller (+1-555-03{i:02d})",
            "description": f"Material supply batch {i}.",
            "ground_truth_classification": "BEFORE_CUTOFF",  # Revenue/expense belongs to Dec
            "ground_truth_event_date": receipt_date,
            "ground_truth_reason": f"Goods were physically received on {receipt_date} (Dec 2026) prior to the cutoff, despite the invoice being dated {invoice_date} and posted in January.",
            "evidence_text": f"DHL Shipping Portal. Waybill PO-C{i:02d}. Status: DELIVERED. Date: Dec {28+i%3}, 2026. Signed by D. Miller (+1-555-03{i:02d}). Vendor ABC Corp routing payments to bank account 1022-9381-C{i:02d}."
        })

    # -------------------------------------------------------------
    # 4. CATEGORY D: AMBIGUOUS RESOLVABLE AFTER CUTOFF (10 cases)
    # -------------------------------------------------------------
    # Posted in December 2026, but delivery actually occurred in January 2027 (e.g. shipped FOB Destination).
    for i in range(1, 11):
        tx_id = f"TXN-D{i:02d}"
        po_id = f"PO-D{i:02d}"
        grn_id = f"GRN-D{i:02d}"
        invoice_id = f"INV-D{i:02d}"
        payment_id = f"PAY-D{i:02d}"
        
        amount = 15000 + i * 4000
        tx_date = "2026-12-18"
        posting_date = "2026-12-30"  # Posted early in December
        receipt_date = f"2027-01-0{2+i%3}"  # Jan 2, 3, 4
        invoice_date = "2026-12-29"   # Invoiced early
        payment_date = "2027-01-10"
        
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-4{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026", # Accrued in Dec, but delivery in Jan.
            "po_date": tx_date,
            "ship_date": "2026-12-30",
            "delivery_date": receipt_date,
            "grn_date": receipt_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "FedEx Freight",
            "received_by": f"Receiving Operator Bob Vance (+1-555-04{i:02d})",
            "description": f"Industrial equipment parts batch {i}.",
            "ground_truth_classification": "AFTER_CUTOFF",  # Revenue/expense belongs to Jan
            "ground_truth_event_date": receipt_date,
            "ground_truth_reason": f"Goods were delivered on {receipt_date} (January 2027) which is after the cutoff date. The transaction was prematurely posted in December 2026 based on the early invoice date {invoice_date}.",
            "evidence_text": f"FedEx Freight Delivery Note {po_id}. Consignee Bob Vance (+1-555-04{i:02d}) verified receipt of machinery components on Jan 0{2+i%3}, 2027. FOB Destination terms applied. Settlement route bank 2291-0391-D{i:02d}."
        })

    # -------------------------------------------------------------
    # 5. CATEGORY E: MISSING EVIDENCE / UNRESOLVED (5 cases)
    # -------------------------------------------------------------
    # Invoices/payments exist around cutoff, but absolutely no delivery confirmation or goods receipt records are available.
    for i in range(1, 6):
        tx_id = f"TXN-E{i:02d}"
        po_id = f"PO-E{i:02d}"
        invoice_id = f"INV-E{i:02d}"
        payment_id = f"PAY-E{i:02d}"
        
        amount = 20000 + i * 5000
        tx_date = "2026-12-22"
        posting_date = "2026-12-29"
        invoice_date = "2026-12-28"
        payment_date = "2027-01-04"
        
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-5{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026",
            "po_date": tx_date,
            "ship_date": None,        # Shipment record missing!
            "delivery_date": None,    # Delivery confirmation missing!
            "grn_date": None,         # Goods Receipt missing!
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": None,
            "received_by": None,
            "description": f"Strategic raw material reserves {i}.",
            "ground_truth_classification": "UNRESOLVED",
            "ground_truth_event_date": None,
            "ground_truth_reason": "No Shipment or Goods Receipt record exists. It is impossible to determine when the physical delivery or transfer of control occurred.",
            "evidence_text": f"Internal email from Accounting: 'Please find attached invoice {invoice_id} for purchase order {po_id}. We are still waiting on the warehouse team to upload the signed goods receipt note. Address: 456 Oak Rd, Boston, MA. Contact clerk Jane Smith (+1-555-05{i:02d}).'"
        })

    # -------------------------------------------------------------
    # 6. CATEGORY F: CONFLICTING EVIDENCE / UNRESOLVED / MISSTATEMENT (5 cases)
    # -------------------------------------------------------------
    # Goods receipt date states one thing, but carrier shipping logs / customer emails state another date.
    for i in range(1, 6):
        tx_id = f"TXN-F{i:02d}"
        po_id = f"PO-F{i:02d}"
        grn_id = f"GRN-F{i:02d}"
        invoice_id = f"INV-F{i:02d}"
        payment_id = f"PAY-F{i:02d}"
        
        amount = 35000 + i * 10000
        tx_date = "2026-12-15"
        posting_date = "2026-12-31"
        grn_date = "2026-12-29" # Internal record claims Dec 29 delivery
        invoice_date = "2026-12-30"
        payment_date = "2027-01-08"
        
        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-6{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026",
            "po_date": tx_date,
            "ship_date": "2026-12-28",
            "delivery_date": "2027-01-03", # Carrier log contradicts internal GRN (claims Jan 03)
            "grn_date": grn_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "DHL Express",
            "received_by": f"Receiving Manager Robert Smith (+1-555-06{i:02d})",
            "description": f"Server hardware configuration {i}.",
            "ground_truth_classification": "POTENTIAL_MISSTATEMENT",  # Because of contradiction & actual delivery in Jan
            "ground_truth_event_date": "2027-01-03",
            "ground_truth_reason": f"There is a severe contradiction: internal Goods Receipt shows delivery on {grn_date}, but DHL carrier tracking and vendor email confirm delivery occurred on 2027-01-03, after the cutoff.",
            "evidence_text": f"DHL System log: Package delivered and signed by R. Smith (+1-555-06{i:02d}) on Jan 03, 2027. Vendor email thread: 'Hi team, we apologize for the delay. The server rack left our facility late and was delivered to your Boston warehouse on January 3rd. Standard terms apply. Bank routing 9021-3921-F{i:02d}.'"
        })

            # -------------------------------------------------------------
    # 7. CATEGORY G: DATA QUALITY EXCEPTION (5 cases)
    # -------------------------------------------------------------
    # Invoice amount is corrupted/mismatched from the transaction amount — a data entry error, not a timing question.
    for i in range(1, 6):
        tx_id = f"TXN-G{i:02d}"
        po_id = f"PO-G{i:02d}"
        grn_id = f"GRN-G{i:02d}"
        invoice_id = f"INV-G{i:02d}"
        payment_id = f"PAY-G{i:02d}"

        amount = 8000 + i * 1500
        bad_invoice_amount = amount * 1.75  # ~75% mismatch — clearly corrupted, not a rounding difference
        tx_date = "2026-12-12"
        posting_date = "2026-12-27"
        receipt_date = "2026-12-27"
        invoice_date = "2026-12-28"
        payment_date = "2027-01-06"

        cases.append({
            "type": "goods_purchase",
            "tx_id": tx_id,
            "po_id": po_id,
            "vendor_id": f"VEN-7{i:02d}",
            "customer_id": None,
            "amount": amount,
            "invoice_amount": bad_invoice_amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026",
            "po_date": tx_date,
            "ship_date": "2026-12-23",
            "delivery_date": receipt_date,
            "grn_date": receipt_date,
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "carrier": "USPS Priority",
            "received_by": f"Dock Supervisor Alan Grant (+1-555-07{i:02d})",
            "description": f"Batch materials order {i} (data quality test case).",
            "ground_truth_classification": "DATA_QUALITY_EXCEPTION",
            "ground_truth_event_date": None,
            "ground_truth_reason": f"Invoice amount ({bad_invoice_amount}) does not reconcile with transaction amount ({amount}) — likely data entry error requiring correction before cutoff testing can proceed.",
            "evidence_text": f"Accounts Payable note: Invoice {invoice_id} amount flagged by automated three-way match as inconsistent with PO {po_id} and transaction amount. Reviewer: Alan Grant (+1-555-07{i:02d}). Requires correction before period-end close."
        })

        # -------------------------------------------------------------
    # 8. CATEGORY H: SERVICE/CONTRACT TRANSACTIONS (10 cases)
    # -------------------------------------------------------------
    # Consulting/service transactions resolved via ServiceRecord + Contract, not GRN/shipment.
    for i in range(1, 11):
        tx_id = f"TXN-H{i:02d}"
        contract_id = f"CON-H{i:02d}"
        service_id = f"SRV-H{i:02d}"
        invoice_id = f"INV-H{i:02d}"
        payment_id = f"PAY-H{i:02d}"

        amount = 18000 + i * 2500
        tx_date = "2026-12-08"
        # Alternate: half complete clearly before cutoff, half clearly after
        if i <= 5:
            service_start = "2026-12-10"
            service_end = "2026-12-27"
            completion_status = "COMPLETED"
            posting_date = "2026-12-29"
            invoice_date = "2026-12-28"
            ground_truth_classification = "BEFORE_CUTOFF"
            reason = f"Service was fully completed on {service_end} (Dec 2026), before the cutoff of 2026-12-31."
        else:
            service_start = "2026-12-20"
            service_end = "2027-01-05"
            completion_status = "COMPLETED"
            posting_date = "2026-12-30"
            invoice_date = "2026-12-29"
            ground_truth_classification = "AFTER_CUTOFF"
            reason = f"Service was not completed until {service_end} (Jan 2027), after the cutoff of 2026-12-31, despite early invoicing."
        payment_date = "2027-01-10"

        cases.append({
            "type": "service_purchase",
            "tx_id": tx_id,
            "po_id": None,
            "vendor_id": f"VEN-8{i:02d}",
            "customer_id": None,
            "amount": amount,
            "tx_date": tx_date,
            "posting_date": posting_date,
            "ledger_period": "December 2026",
            "invoice_date": invoice_date,
            "payment_date": payment_date,
            "description": f"Consulting engagement {i}.",
            "ground_truth_classification": ground_truth_classification,
            "ground_truth_event_date": service_end,
            "ground_truth_reason": reason,
            "contract_effective_date": tx_date,
            "contract_service_period": "3 months",
            "contract_terms": f"Standard consulting terms. Contact billing coordinator Nancy Drew (+1-555-08{i:02d}) for invoicing queries.",
            "service_start": service_start,
            "service_end": service_end,
            "completion_status": completion_status,
            "evidence_text": f"Service completion sign-off for {contract_id}: work completed and accepted by client on {service_end}. Signed off by project lead Nancy Drew (+1-555-08{i:02d})."
        })

    # Save to Database and Ground Truth Dictionary
    for case in cases:
        tx_id = case["tx_id"]
        
        # 1. Create Transaction
        db_tx = Transaction(
            transaction_id=tx_id,
            transaction_type=case["type"],
            amount=case["amount"],
            currency="INR",
            transaction_date=parse_date(case["tx_date"]),
            posting_date=parse_date(case["posting_date"]),
            ledger_period=case["ledger_period"],
            vendor_id=case["vendor_id"],
            customer_id=case["customer_id"],
            status="PENDING"
        )
        db.add(db_tx)
        db.commit()
        
                # Create Contract + ServiceRecord for service-type cases
        if case.get("contract_effective_date"):
            db_contract = Contract(
                contract_id=f"CON-{tx_id.split('-')[1]}",
                transaction_id=tx_id,
                effective_date=parse_date(case["contract_effective_date"]),
                service_period=case["contract_service_period"],
                terms=case["contract_terms"]
            )
            db.add(db_contract)
            db.commit()

        if case.get("service_start"):
            db_service = ServiceRecord(
                service_id=f"SRV-{tx_id.split('-')[1]}",
                transaction_id=tx_id,
                service_start=parse_date(case["service_start"]),
                service_end=parse_date(case["service_end"]),
                completion_status=case["completion_status"]
            )
            db.add(db_service)
            db.commit()
            
        # 2. Create PO if exists
        if case.get("po_id"):
            db_po = PurchaseOrder(
                po_id=case["po_id"],
                transaction_id=tx_id,
                vendor_id=case["vendor_id"],
                po_date=parse_date(case["po_date"]),
                amount=case["amount"],
                description=case["description"]
            )
            db.add(db_po)
            db.commit()
            
            # Create Shipment
            if case.get("ship_date"):
                db_ship = Shipment(
                    shipment_id=f"SHIP-{case['po_id'].split('-')[1]}",
                    po_id=case["po_id"],
                    ship_date=parse_date(case["ship_date"]),
                    delivery_date=parse_date(case["delivery_date"]),
                    carrier=case["carrier"]
                )
                db.add(db_ship)
                db.commit()
                
            # Create Goods Receipt
            if case.get("grn_date"):
                db_grn = GoodsReceipt(
                    grn_id=f"GRN-{case['po_id'].split('-')[1]}",
                    po_id=case["po_id"],
                    receipt_date=parse_date(case["grn_date"]),
                    quantity=10,
                    received_by=case["received_by"]
                )
                db.add(db_grn)
                db.commit()

        # 3. Create Invoice
        if case.get("invoice_date"):
            db_inv = Invoice(
                invoice_id=f"INV-{tx_id.split('-')[1]}",
                transaction_id=tx_id,
                invoice_date=parse_date(case["invoice_date"]),
                amount=case.get("invoice_amount", case["amount"]),
                tax=case["amount"] * 0.05,
                vendor_id=case["vendor_id"]
            )
            db.add(db_inv)
            db.commit()

        # 4. Create Payment
        if case.get("payment_date"):
            db_pay = Payment(
                payment_id=f"PAY-{tx_id.split('-')[1]}",
                transaction_id=tx_id,
                payment_date=parse_date(case["payment_date"]),
                amount=case["amount"],
                payment_method="Wire Transfer"
            )
            db.add(db_pay)
            db.commit()
            
        # 5. Create Evidence documents (unstructured)
        add_evidence_record(
            db=db,
            evidence_id=f"EVID-{tx_id.split('-')[1]}",
            transaction_id=tx_id,
            source_type="carrier_log" if case.get("carrier") else "accounting_note",
            source_record=case["po_id"] if case.get("po_id") else tx_id,
            content=case["evidence_text"],
            relevant_date=parse_date(case["delivery_date"]) if case.get("delivery_date") else parse_date(case["posting_date"]),
            reliability="HIGH"
        )
        
        # Populate Ground Truth
        ground_truth[tx_id] = {
            "classification": case["ground_truth_classification"],
            "economic_event_date": case["ground_truth_event_date"],
            "reason": case["ground_truth_reason"]
        }

    # Write ground truth JSON file
    with open("backend/data/ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)

    db.close()
    print(f"Database successfully seeded with {len(cases)} transactions around period cutoff 2026-12-31.")

if __name__ == "__main__":
    generate_synthetic_data()
