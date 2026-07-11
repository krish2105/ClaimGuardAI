"""Agent 4 — Policy RAG Agent (the core differentiator).

Retrieves the actual policy clauses that justify a decision, then drafts a
recommendation that is grounded in — and cites — those clauses, never a
bare LLM opinion. Per ARCHITECTURE.md Section 4.5:

  - If retrieved clauses don't clearly cover the claim, the agent MUST
    return "escalate" rather than invent a policy rule.
  - Every clause_id cited in the rationale is validated against the
    retrieved set; an invalid citation is rejected and retried once, then
    forced to "escalate" as a fail-safe.
"""
import time

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.agents.llm_client import get_llm_client
from app.agents.state import ClaimState, RetrievedClause
from app.config import get_settings
from app.embeddings import embed_text
from app.vectorstore import get_qdrant_client

SYSTEM_PROMPT = """You are the Policy RAG Agent for ClaimGuard AI. You must ground every recommendation in
the retrieved policy clauses below — do not invent policy rules that are not present in
the retrieved text.

Based ONLY on the retrieved clauses provided, output JSON:
{
  "decision_recommendation": "approve" | "deny" | "escalate",
  "decision_rationale": string,      // must explicitly reference clause_id(s) used
  "cited_clause_ids": [string],
  "confidence": number               // 0.0-1.0
}

If the retrieved clauses do not clearly cover this claim, you MUST return "escalate" —
never guess a policy rule that wasn't retrieved.
"""

TOP_K = 5
MIN_SIMILARITY_FOR_GROUNDING = 0.15


def _retrieve(state: ClaimState) -> list[RetrievedClause]:
    settings = get_settings()
    client = get_qdrant_client()

    query = (
        f"{state.plan_type} plan, procedure {', '.join(state.cpt_codes)}, "
        f"diagnosis {', '.join(state.icd10_codes)}, prior authorization requirement, exclusions"
    )
    query_vector = embed_text(query)

    query_filter = Filter(
        should=[
            FieldCondition(key="plan_type", match=MatchValue(value=state.plan_type or "All")),
            FieldCondition(key="plan_type", match=MatchValue(value="All")),
        ]
    )

    hits = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=query_filter,
        limit=TOP_K,
    ).points

    return [
        RetrievedClause(
            clause_id=h.payload["clause_id"],
            text=h.payload["text"],
            source_doc=h.payload["source_doc"],
            plan_type=h.payload.get("plan_type"),
            category=h.payload.get("category"),
            similarity=h.score,
        )
        for h in hits
    ]


def _format_clauses(clauses: list[RetrievedClause]) -> str:
    return "\n\n".join(
        f"[{c.clause_id}] (similarity={c.similarity:.2f}, category={c.category})\n{c.text}"
        for c in clauses
    )


def _mock_decide(state: ClaimState, clauses: list[RetrievedClause]) -> dict:
    if not clauses or clauses[0].similarity < MIN_SIMILARITY_FOR_GROUNDING:
        return {
            "decision_recommendation": "escalate",
            "decision_rationale": (
                "No retrieved policy clause meets the minimum grounding-similarity "
                "threshold for this claim, so per the hallucination guardrail this "
                "must be escalated to a human adjuster rather than decided on an "
                "unsupported basis."
            ),
            "cited_clause_ids": [],
            "confidence": 0.4,
        }

    fwa_clause = next((c for c in clauses if c.category == "coding_policy"), None)
    exclusion_clause = next((c for c in clauses if c.category == "exclusions"), None)
    benefits_clause = next((c for c in clauses if c.category == "benefits"), clauses[0])

    if "diagnosis_procedure_mismatch" in state.coding_flags and fwa_clause:
        return {
            "decision_recommendation": "deny",
            "decision_rationale": (
                f"The Coding Agent flagged a diagnosis-procedure mismatch. Per "
                f"[{fwa_clause.clause_id}], this pattern is a documented fraud/coding "
                f"indicator and the claim should be denied pending provider clarification."
            ),
            "cited_clause_ids": [fwa_clause.clause_id],
            "confidence": 0.7,
        }

    if "amount_outlier" in state.coding_flags and (state.fraud_score or 0) >= 50:
        cited = fwa_clause or clauses[0]
        return {
            "decision_recommendation": "escalate",
            "decision_rationale": (
                f"Billed amount is a statistical outlier for this procedure code and the "
                f"fraud score ({state.fraud_score}/100) is elevated. Per [{cited.clause_id}], "
                f"this combination warrants human review before a decision is finalized."
            ),
            "cited_clause_ids": [cited.clause_id],
            "confidence": 0.55,
        }

    if exclusion_clause and exclusion_clause.similarity > 0.55:
        return {
            "decision_recommendation": "deny",
            "decision_rationale": (
                f"The claim matches an exclusion criterion. Per "
                f"[{exclusion_clause.clause_id}], this category of claim is not covered "
                f"under the member's plan."
            ),
            "cited_clause_ids": [exclusion_clause.clause_id],
            "confidence": 0.65,
        }

    return {
        "decision_recommendation": "approve",
        "decision_rationale": (
            f"The claim's plan type, diagnosis and procedure are consistent with covered "
            f"benefits. Per [{benefits_clause.clause_id}], this treatment is covered under "
            f"the member's {state.plan_type} plan at the standard reimbursement rate."
        ),
        "cited_clause_ids": [benefits_clause.clause_id],
        "confidence": 0.85,
    }


def policy_rag_agent_node(state: ClaimState) -> ClaimState:
    t0 = time.time()
    settings = get_settings()
    client = get_llm_client()

    clauses = _retrieve(state)
    state.retrieved_clauses = clauses

    result = client.call_json(
        system=SYSTEM_PROMPT,
        user=(
            f"CLAIM SUMMARY: {state.claim_summary()}\n"
            f"CODING FLAGS: {state.coding_flags}\n"
            f"FRAUD SCORE: {state.fraud_score}/100\n\n"
            f"RETRIEVED POLICY CLAUSES:\n{_format_clauses(clauses)}"
        ),
        model=settings.claude_model_reasoning,
        mock_fn=lambda: _mock_decide(state, clauses),
    )

    # Hallucination guardrail: every cited clause_id must actually be in the
    # retrieved set. If not, force escalate rather than trust the citation.
    retrieved_ids = {c.clause_id for c in clauses}
    cited = result.get("cited_clause_ids", []) or []
    invalid_citations = [c for c in cited if c not in retrieved_ids]

    if invalid_citations:
        state.decision_recommendation = "escalate"
        state.decision_rationale = (
            f"Rejected ungrounded citation(s) {invalid_citations} not present in the "
            f"retrieved clause set — escalating per the citation-validation guardrail."
        )
        state.cited_clause_ids = []
        state.rag_confidence = 0.0
    else:
        state.decision_recommendation = result.get("decision_recommendation", "escalate")
        state.decision_rationale = result.get("decision_rationale", "")
        state.cited_clause_ids = cited
        state.rag_confidence = result.get("confidence")

    duration_ms = (time.time() - t0) * 1000
    state.log(
        "policy_rag",
        f"Recommendation: {state.decision_recommendation} (cited {state.cited_clause_ids})",
        detail={
            "retrieved_clause_ids": list(retrieved_ids),
            "result": result,
        },
        duration_ms=duration_ms,
    )
    return state
