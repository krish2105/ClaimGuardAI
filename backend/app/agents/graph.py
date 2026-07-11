"""LangGraph wiring for the 5-agent ClaimGuard AI pipeline.

Section 4.7 of ARCHITECTURE.md. The only conditional edge is after Intake:
if extraction fails, the claim is routed straight to END already marked
`escalated`, rather than letting downstream agents run on incomplete state.
"""
from langgraph.graph import END, StateGraph

from app.agents.coding_agent import coding_agent_node
from app.agents.decision_router import decision_router_node
from app.agents.fraud_scoring_agent import fraud_scoring_node
from app.agents.intake_agent import intake_agent_node
from app.agents.policy_rag_agent import policy_rag_agent_node
from app.agents.state import ClaimState


def _route_after_intake(state: ClaimState) -> str:
    return "escalate" if state.error else "continue"


def build_graph():
    graph = StateGraph(ClaimState)
    graph.add_node("intake", intake_agent_node)
    graph.add_node("coding", coding_agent_node)
    graph.add_node("fraud_scoring", fraud_scoring_node)
    graph.add_node("policy_rag", policy_rag_agent_node)
    graph.add_node("decision_router", decision_router_node)

    graph.set_entry_point("intake")
    graph.add_conditional_edges(
        "intake", _route_after_intake, {"continue": "coding", "escalate": END}
    )
    graph.add_edge("coding", "fraud_scoring")
    graph.add_edge("fraud_scoring", "policy_rag")
    graph.add_edge("policy_rag", "decision_router")
    graph.add_edge("decision_router", END)

    return graph.compile()


claim_pipeline = build_graph()
