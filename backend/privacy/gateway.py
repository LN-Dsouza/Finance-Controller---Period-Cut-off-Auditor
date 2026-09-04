import re
import hashlib

# Regular expressions for PII detection
EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
BANK_ACCOUNT_REGEX = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b|\b\d{8,12}\b')
STREET_ADDRESS_REGEX = re.compile(r'\d+\s+[A-Za-z0-9\s,]{4,}\b(?:Avenue|Lane|Road|Boulevard|Drive|Street|Ave|Dr|Rd|Blvd|St|Way|Ct|Pl)\b', re.IGNORECASE)

class PrivacyGateway:
    def __init__(self):
        # Maps raw PII -> stable pseudonymous token
        self.pii_map = {}
        self.counter = {
            "EMAIL": 1,
            "PHONE": 1,
            "BANK": 1,
            "ADDRESS": 1,
            "NAME": 1
        }

    def _get_token(self, pii_type: str, raw_value: str) -> str:
        """Retrieves or creates a stable token for a given raw PII value."""
        cleaned_val = raw_value.strip().lower()
        key = f"{pii_type}:{cleaned_val}"
        
        if key not in self.pii_map:
            num = self.counter[pii_type]
            token = f"[{pii_type}_{num}]"
            self.pii_map[key] = token
            self.counter[pii_type] += 1
            
        return self.pii_map[key]

    def redact_text(self, text: str) -> str:
        """Scans the text and replaces PII matches with stable tokens."""
        if not text:
            return ""

        # Redact Emails
        def email_repl(match):
            return self._get_token("EMAIL", match.group(0))
        text = EMAIL_REGEX.sub(email_repl, text)

        # Redact Phone Numbers
        def phone_repl(match):
            return self._get_token("PHONE", match.group(0))
        text = PHONE_REGEX.sub(phone_repl, text)

        # Redact Bank Accounts
        def bank_repl(match):
            return self._get_token("BANK", match.group(0))
        text = BANK_ACCOUNT_REGEX.sub(bank_repl, text)

        # Redact Addresses
        def addr_repl(match):
            return self._get_token("ADDRESS", match.group(0))
        text = STREET_ADDRESS_REGEX.sub(addr_repl, text)

        return text

    def minimize_transaction(self, tx) -> dict:
        """Redacts sensitive direct identifiers from a structured Transaction record."""
        return {
            "transaction_id": tx.transaction_id,
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "currency": tx.currency,
            "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
            "posting_date": tx.posting_date.isoformat() if tx.posting_date else None,
            "ledger_period": tx.ledger_period,
            "vendor_id": tx.vendor_id,
            "customer_id": tx.customer_id
        }

    def minimize_invoice(self, inv) -> dict:
        """Redacts invoice details for secure AI retrieval."""
        return {
            "invoice_id": inv.invoice_id,
            "transaction_id": inv.transaction_id,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "amount": inv.amount,
            "tax": inv.tax,
            "vendor_id": inv.vendor_id
        }

    def minimize_purchase_order(self, po) -> dict:
        """Redacts PO descriptions and PII."""
        return {
            "po_id": po.po_id,
            "transaction_id": po.transaction_id,
            "vendor_id": po.vendor_id,
            "po_date": po.po_date.isoformat() if po.po_date else None,
            "amount": po.amount,
            "description": self.redact_text(po.description)
        }

    def minimize_goods_receipt(self, grn) -> dict:
        return {
            "grn_id": grn.grn_id,
            "po_id": grn.po_id,
            "receipt_date": grn.receipt_date.isoformat() if grn.receipt_date else None,
            "quantity": grn.quantity,
            "received_by": self._get_token("NAME", grn.received_by) if grn.received_by else None
        }

    def minimize_shipment(self, ship) -> dict:
        return {
            "shipment_id": ship.shipment_id,
            "po_id": ship.po_id,
            "ship_date": ship.ship_date.isoformat() if ship.ship_date else None,
            "delivery_date": ship.delivery_date.isoformat() if ship.delivery_date else None,
            "carrier": ship.carrier
        }

    def minimize_payment(self, pay) -> dict:
        return {
            "payment_id": pay.payment_id,
            "transaction_id": pay.transaction_id,
            "payment_date": pay.payment_date.isoformat() if pay.payment_date else None,
            "amount": pay.amount,
            "payment_method": pay.payment_method
        }


# Module-level shared instance so PII tokens stay consistent across ingestion and retrieval
default_gateway = PrivacyGateway()
