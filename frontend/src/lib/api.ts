import type {
  ClaimDetail,
  ClaimListResponse,
  ClaimSubmitRequest,
  ClaimSubmitResponse,
  DecisionTraceResponse,
  EscalationItem,
  FraudTrendsResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL || "ws://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new Error("Could not reach the ClaimGuard AI server. Check your connection and try again.");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      if (typeof parsed?.detail === "string") detail = parsed.detail;
    } catch {
      // not JSON — fall back to the raw body text
    }
    if (res.status === 429) {
      throw new Error("Too many requests — please wait a moment and try again.");
    }
    throw new Error(detail || `Request failed (${res.status}).`);
  }
  return res.json();
}

export function listClaims(params: {
  status?: string;
  plan_type?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ClaimListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.plan_type) search.set("plan_type", params.plan_type);
  search.set("limit", String(params.limit ?? 50));
  search.set("offset", String(params.offset ?? 0));
  return apiFetch(`/claims?${search.toString()}`);
}

export function getClaim(claimId: string): Promise<ClaimDetail> {
  return apiFetch(`/claims/${claimId}`);
}

export function getDecisionTrace(claimId: string): Promise<DecisionTraceResponse> {
  return apiFetch(`/claims/${claimId}/decision-trace`);
}

export function submitClaim(payload: ClaimSubmitRequest): Promise<ClaimSubmitResponse> {
  return apiFetch(`/claims/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listEscalations(status: string = "pending"): Promise<EscalationItem[]> {
  return apiFetch(`/escalations?status=${status}`);
}

export function resolveEscalation(
  escalationId: number,
  payload: { adjuster_decision: "approve" | "deny"; adjuster_notes?: string }
): Promise<EscalationItem> {
  return apiFetch(`/escalations/${escalationId}/resolve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFraudTrends(): Promise<FraudTrendsResponse> {
  return apiFetch(`/analytics/fraud-trends`);
}
