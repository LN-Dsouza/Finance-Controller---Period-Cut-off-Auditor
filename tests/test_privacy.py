from backend.privacy.gateway import PrivacyGateway
from backend.agents.prompts import PROMPT_INJECTION_DEFENSE_FOOTER, MAKE_DECISION_PROMPT
from tests.conftest import add_goods_case


def test_redacts_phone_bank_and_email():
    gw = PrivacyGateway()
    text = "Call Jane at 415-555-0123 or jane@vendor.com. Bank 4820-1923-4455-6677"
    redacted = gw.redact_text(text)
    assert "415-555-0123" not in redacted
    assert "jane@vendor.com" not in redacted
    assert "[PHONE_" in redacted
    assert "[EMAIL_" in redacted
    assert "[BANK_" in redacted


def test_tokenization_is_stable():
    gw = PrivacyGateway()
    a = gw.redact_text("Reach 415-555-0199")
    b = gw.redact_text("Reach 415-555-0199")
    assert a == b


def test_minimize_transaction_omits_status_and_pii_fields(db):
    tx = add_goods_case(
        db, "TXN-PII",
        tx_date="2026-12-10",
        posting_date="2026-12-28",
        invoice_date="2026-12-29",
        grn_date="2026-12-28",
        ship_date="2026-12-24",
        delivery_date="2026-12-28",
    )
    minimized = PrivacyGateway().minimize_transaction(tx)
    assert "status" not in minimized
    assert minimized["vendor_id"] == "VEN-TEST"


def test_prompts_separate_instructions_from_evidence():
    assert "untrusted" in PROMPT_INJECTION_DEFENSE_FOOTER.lower()
    assert "<evidence_bundle>" in MAKE_DECISION_PROMPT
    assert "IGNORE THEM" in PROMPT_INJECTION_DEFENSE_FOOTER