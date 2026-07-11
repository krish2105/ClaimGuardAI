export type PlanType = "Basic" | "Enhanced" | "Thiqa" | "Comprehensive";
export type Recommendation = "approve" | "deny" | "escalate";
export type FinalDecision = "auto_approved" | "auto_denied" | "escalated";

export interface ClaimListItem {
  claim_id: string;
  patient_id: string;
  provider_id: string | null;
  plan_type: PlanType | null;
  billed_amount: number | null;
  treatment_date: string | null;
  fraud_score: number | null;
  coding_flags: string[];
  decision_recommendation: Recommendation | null;
  final_decision: FinalDecision | null;
  created_at: string | null;
}

export interface ClaimListResponse {
  total: number;
  items: ClaimListItem[];
}

export interface RetrievedClause {
  clause_id: string;
  text: string;
  source_doc: string;
  plan_type?: string | null;
  category?: string | null;
  similarity: number;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface ClaimDetail extends ClaimListItem {
  icd10_codes: string[];
  cpt_codes: string[];
  approved_amount: number | null;
  prior_auth_required: boolean | null;
  prior_auth_obtained: boolean | null;
  fraud_top_features: FeatureContribution[];
  retrieved_clauses: RetrievedClause[];
  decision_rationale: string | null;
  escalation_reason: string | null;
}

export interface TraceStep {
  agent: string;
  status: "started" | "completed" | "failed";
  summary: string;
  detail: Record<string, unknown>;
  duration_ms: number | null;
  timestamp?: string | null;
}

export interface DecisionTraceResponse {
  claim_id: string;
  final_decision: FinalDecision | null;
  agent_trace: TraceStep[];
}

export interface EscalationItem {
  escalation_id: number;
  claim_id: string;
  status: "pending" | "resolved";
  adjuster_decision: "approve" | "deny" | null;
  adjuster_notes: string | null;
  created_at: string | null;
  resolved_at: string | null;
  fraud_score: number | null;
  escalation_reason: string | null;
  plan_type: string | null;
  billed_amount: number | null;
}

export interface FraudTrendPoint {
  period: string;
  total_claims: number;
  escalated: number;
  auto_approved: number;
  auto_denied: number;
  avg_fraud_score: number;
}

export interface CodingFlagCount {
  flag: string;
  count: number;
}

export interface FraudTrendsResponse {
  trend: FraudTrendPoint[];
  coding_flag_frequency: CodingFlagCount[];
  escalation_rate: number;
  total_claims_processed: number;
  plan_type_breakdown: Record<string, number>;
}

export interface ClaimSubmitRequest {
  patient_id: string;
  provider_id: string;
  plan_type: PlanType;
  treatment_date: string;
  icd10_codes: string[];
  cpt_codes: string[];
  billed_amount: number;
  notes?: string;
}

export interface ClaimSubmitResponse {
  claim_id: string;
  status: string;
  ws_url: string;
}

export interface StreamMessage {
  type: "step" | "final" | "done";
  agent?: string;
  summary?: string;
  status?: string;
  final_decision?: FinalDecision;
  state?: Record<string, unknown>;
}
