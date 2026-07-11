from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class ClaimSubmitRequest(BaseModel):
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    plan_type: Optional[Literal["Basic", "Enhanced", "Thiqa", "Comprehensive"]] = None
    treatment_date: Optional[str] = None
    icd10_codes: Optional[list[str]] = None
    cpt_codes: Optional[list[str]] = None
    billed_amount: Optional[float] = None
    notes: Optional[str] = None
    raw_document_text: Optional[str] = None


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    status: str = "processing"
    ws_url: str


class ClaimListItem(BaseModel):
    claim_id: str
    patient_id: str
    provider_id: Optional[str] = None
    plan_type: Optional[str] = None
    billed_amount: Optional[float] = None
    treatment_date: Optional[date] = None
    fraud_score: Optional[float] = None
    coding_flags: list[str] = []
    decision_recommendation: Optional[str] = None
    final_decision: Optional[str] = None
    created_at: Optional[datetime] = None


class ClaimListResponse(BaseModel):
    total: int
    items: list[ClaimListItem]


class ClaimDetail(ClaimListItem):
    icd10_codes: list[str] = []
    cpt_codes: list[str] = []
    approved_amount: Optional[float] = None
    prior_auth_required: Optional[bool] = None
    prior_auth_obtained: Optional[bool] = None
    fraud_top_features: list[dict] = []
    retrieved_clauses: list[dict] = []
    decision_rationale: Optional[str] = None
    escalation_reason: Optional[str] = None


class TraceStep(BaseModel):
    agent: str
    status: str
    summary: str
    detail: dict[str, Any] = {}
    duration_ms: Optional[float] = None
    timestamp: Optional[datetime] = None


class DecisionTraceResponse(BaseModel):
    claim_id: str
    final_decision: Optional[str] = None
    agent_trace: list[TraceStep] = []


class EscalationItem(BaseModel):
    escalation_id: int
    claim_id: str
    status: str
    adjuster_decision: Optional[str] = None
    adjuster_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    fraud_score: Optional[float] = None
    escalation_reason: Optional[str] = None
    plan_type: Optional[str] = None
    billed_amount: Optional[float] = None


class EscalationResolveRequest(BaseModel):
    adjuster_decision: Literal["approve", "deny"]
    adjuster_notes: Optional[str] = None


class FraudTrendPoint(BaseModel):
    period: str
    total_claims: int
    escalated: int
    auto_approved: int
    auto_denied: int
    avg_fraud_score: float


class CodingFlagCount(BaseModel):
    flag: str
    count: int


class FraudTrendsResponse(BaseModel):
    trend: list[FraudTrendPoint]
    coding_flag_frequency: list[CodingFlagCount]
    escalation_rate: float
    total_claims_processed: int
    plan_type_breakdown: dict[str, int]
