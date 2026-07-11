"""Shared state object threaded through every LangGraph node.

Every agent reads from and writes to this object. The frontend renders the
`agent_trace` list as a step-by-step decision trace, so agents must append to
it rather than overwrite it.
"""
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

PlanType = Literal["Basic", "Enhanced", "Thiqa", "Comprehensive"]
Recommendation = Literal["approve", "deny", "escalate"]
FinalDecision = Literal["auto_approved", "auto_denied", "escalated"]


class RetrievedClause(BaseModel):
    clause_id: str
    text: str
    source_doc: str
    plan_type: Optional[str] = None
    category: Optional[str] = None
    similarity: float = 0.0


class FeatureContribution(BaseModel):
    feature: str
    value: float
    contribution: float  # signed SHAP-style contribution to the fraud score


class AgentTraceStep(BaseModel):
    agent: str
    status: Literal["started", "completed", "failed"] = "completed"
    summary: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None


class ClaimState(BaseModel):
    claim_id: str
    raw_document_text: str = ""
    raw_document_path: Optional[str] = None

    # --- Populated by Intake Agent ---
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    icd10_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)
    billed_amount: Optional[float] = None
    treatment_date: Optional[date] = None
    plan_type: Optional[PlanType] = None
    intake_confidence: Optional[float] = None

    # --- Populated by Coding Agent ---
    coding_flags: list[str] = Field(default_factory=list)
    coding_confidence: Optional[float] = None

    # --- Populated by Fraud Scoring Agent ---
    fraud_score: Optional[float] = None
    fraud_top_features: list[FeatureContribution] = Field(default_factory=list)

    # --- Populated by Policy RAG Agent ---
    retrieved_clauses: list[RetrievedClause] = Field(default_factory=list)
    decision_recommendation: Optional[Recommendation] = None
    decision_rationale: Optional[str] = None
    cited_clause_ids: list[str] = Field(default_factory=list)
    rag_confidence: Optional[float] = None

    # --- Populated by Decision Router ---
    final_decision: Optional[FinalDecision] = None
    escalation_reason: Optional[str] = None

    # --- Cross-cutting ---
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)
    error: Optional[str] = None

    def log(self, agent: str, summary: str, detail: Optional[dict] = None,
            status: str = "completed", duration_ms: Optional[float] = None) -> None:
        self.agent_trace.append(
            AgentTraceStep(
                agent=agent,
                status=status,  # type: ignore[arg-type]
                summary=summary,
                detail=detail or {},
                duration_ms=duration_ms,
            )
        )

    def claim_summary(self) -> str:
        return (
            f"Claim {self.claim_id}: plan={self.plan_type}, "
            f"icd10={self.icd10_codes}, cpt={self.cpt_codes}, "
            f"billed={self.billed_amount} AED, treatment_date={self.treatment_date}"
        )
