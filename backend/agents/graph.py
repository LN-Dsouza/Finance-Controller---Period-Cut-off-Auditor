import os
from langgraph.graph import StateGraph, END
from backend.agents.state import AgentState
from backend.agents.nodes import (
    execute_plan_investigation,
    execute_retrieve_evidence,
    execute_generate_hypotheses,
    execute_verify_hypotheses,
    execute_assess_evidence_sufficiency,
    execute_determine_period,
    execute_escalate_unresolved,
    execute_finalize_decision,
    execute_make_decision
)

def _configure_langsmith():
    tracing = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false")).lower()
    if tracing in ("1", "true", "yes"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
        os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "ai-finance-controller"))

def create_investigation_graph():
    _configure_langsmith()
    workflow = StateGraph(AgentState)

    # Add workflow nodes according to README Section 14
    workflow.add_node("plan_investigation", execute_plan_investigation)
    workflow.add_node("retrieve_evidence", execute_retrieve_evidence)
    workflow.add_node("generate_hypotheses", execute_generate_hypotheses)
    workflow.add_node("verify_hypotheses", execute_verify_hypotheses)
    workflow.add_node("assess_evidence_sufficiency", execute_assess_evidence_sufficiency)
    workflow.add_node("determine_period", execute_determine_period)
    workflow.add_node("escalate_unresolved", execute_escalate_unresolved)
    workflow.add_node("finalize_decision", execute_finalize_decision)

    # Set entry point
    workflow.set_entry_point("plan_investigation")

    # Define edges and conditional routing
    workflow.add_edge("plan_investigation", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "verify_hypotheses")
    workflow.add_edge("verify_hypotheses", "assess_evidence_sufficiency")

    def route_sufficiency(state: AgentState) -> str:
        """Branches based on evidence sufficiency evaluation."""
        if state.get("evidence_sufficiency") == "SUFFICIENT":
            return "determine_period"
        return "escalate_unresolved"

    workflow.add_conditional_edges(
        "assess_evidence_sufficiency",
        route_sufficiency,
        {
            "determine_period": "determine_period",
            "escalate_unresolved": "escalate_unresolved"
        }
    )

    workflow.add_edge("determine_period", "finalize_decision")
    workflow.add_edge("escalate_unresolved", "finalize_decision")
    workflow.add_edge("finalize_decision", END)

    # Compile the graph
    app = workflow.compile()
    return app

# Shared instance of the compiled graph
investigation_graph = create_investigation_graph()
