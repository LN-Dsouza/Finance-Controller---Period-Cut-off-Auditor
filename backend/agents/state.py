from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Inputs
    transaction_id: str
    cutoff_date: str
    transaction_type: str
    candidate_period: str
    
    # Accumulated Evidence
    evidence_ids: List[str]
    structured_evidence: List[Dict[str, Any]]
    semantic_evidence: List[Dict[str, Any]]
    
    # Analysis & Hypotheses
    hypotheses: List[Dict[str, Any]]
    verified_hypotheses: List[Dict[str, Any]]
    contradictions: List[str]
    missing_evidence: List[str]
    known_facts: List[str]

    
    # Decisions
    classification: str             # BEFORE_CUTOFF, AFTER_CUTOFF, POTENTIAL_MISSTATEMENT, UNRESOLVED, DATA_QUALITY_EXCEPTION
    economic_event_date: Optional[str]
    confidence: float               # 0.0 to 1.0
    reasoning_summary: str
    recommended_action: str
    human_review_required: bool
    evidence_sufficiency: Optional[str]   # SUFFICIENT or INSUFFICIENT
    policy_applied: Optional[str]
    
    # Tracking
    steps: List[str]
    tools_called: List[str]
    errors: List[str]
