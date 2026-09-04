"""
Accounting Policy Layer
Implements configurable accounting policies for period-end cut-off testing
according to README Section 8.

Policies define how economic event dates are established for different transaction types:
- Goods: Transfer of control / physical receipt (GRN or carrier delivery).
- Services: Performance obligation satisfaction (service completion).
- Revenue: Performance obligation fulfillment / customer acceptance.
- Unknown: Must escalate for human review.
"""

from typing import Dict, Any, Optional

class AccountingPolicy:
    def __init__(
        self,
        name: str,
        transaction_type: str,
        description: str,
        primary_evidence: str,
        fallback_evidence: Optional[str] = None,
        require_explicit_acceptance: bool = True
    ):
        self.name = name
        self.transaction_type = transaction_type
        self.description = description
        self.primary_evidence = primary_evidence
        self.fallback_evidence = fallback_evidence
        self.require_explicit_acceptance = require_explicit_acceptance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "transaction_type": self.transaction_type,
            "description": self.description,
            "primary_evidence": self.primary_evidence,
            "fallback_evidence": self.fallback_evidence,
            "require_explicit_acceptance": self.require_explicit_acceptance
        }


# Standard Configurable Policies
POLICY_GOODS_TRANSFER_OF_CONTROL = AccountingPolicy(
    name="POLICY-GOODS-CONTROL-TRANSFER",
    transaction_type="goods_purchase",
    description="Transfer of control upon physical receipt (GRN or verified carrier delivery). Invoices and payment dates alone do not establish economic event.",
    primary_evidence="goods_receipt",
    fallback_evidence="carrier_delivery_log",
    require_explicit_acceptance=True
)

POLICY_SERVICE_PERFORMANCE = AccountingPolicy(
    name="POLICY-SERVICE-PERFORMANCE",
    transaction_type="service_purchase",
    description="Performance obligation satisfied upon verified completion of service. Invoices or contract effective dates alone do not establish economic event.",
    primary_evidence="service_completion_record",
    fallback_evidence="signed_contract_terms",
    require_explicit_acceptance=True
)

POLICY_REVENUE_RECOGNITION = AccountingPolicy(
    name="POLICY-REVENUE-RECOGNITION",
    transaction_type="revenue_goods",
    description="Revenue recognition upon customer receipt and transfer of control.",
    primary_evidence="customer_acceptance_or_pod",
    fallback_evidence="carrier_delivery_confirmation",
    require_explicit_acceptance=True
)

POLICY_UNKNOWN_ESCALATION = AccountingPolicy(
    name="POLICY-UNKNOWN-ESCALATION",
    transaction_type="unknown",
    description="Transactions without a recognized accounting policy cannot be auto-cleared and must escalate for human review.",
    primary_evidence="human_review_required",
    fallback_evidence=None,
    require_explicit_acceptance=True
)

POLICIES: Dict[str, AccountingPolicy] = {
    "goods_purchase": POLICY_GOODS_TRANSFER_OF_CONTROL,
    "service_purchase": POLICY_SERVICE_PERFORMANCE,
    "revenue_goods": POLICY_REVENUE_RECOGNITION,
    "revenue_services": POLICY_SERVICE_PERFORMANCE,
}

def get_accounting_policy(transaction_type: str) -> AccountingPolicy:
    """Returns the configured policy for the given transaction type, defaulting to escalation policy."""
    return POLICIES.get(transaction_type, POLICY_UNKNOWN_ESCALATION)

def list_all_policies() -> list:
    """Returns a list of all active accounting policies."""
    seen = {}
    for p in POLICIES.values():
        if p.name not in seen:
            seen[p.name] = p.to_dict()
    seen[POLICY_UNKNOWN_ESCALATION.name] = POLICY_UNKNOWN_ESCALATION.to_dict()
    return list(seen.values())
