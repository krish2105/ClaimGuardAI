"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getClaim, getDecisionTrace } from "@/lib/api";
import type { ClaimDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DecisionBadge, RecommendationBadge } from "@/components/status-badge";
import { FraudScoreMeter } from "@/components/fraud-score-meter";
import { ClauseCard } from "@/components/clause-card";
import { TraceTimeline } from "@/components/trace-timeline";
import { formatAED, formatDate, formatDateTime } from "@/lib/utils";
import type { TraceStep } from "@/lib/types";

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

export default function ClaimDetailPage() {
  const params = useParams<{ claimId: string }>();
  const router = useRouter();
  const [claim, setClaim] = React.useState<ClaimDetail | null>(null);
  const [trace, setTrace] = React.useState<TraceStep[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    Promise.all([getClaim(params.claimId), getDecisionTrace(params.claimId)])
      .then(([claimRes, traceRes]) => {
        setClaim(claimRes);
        setTrace(traceRes.agent_trace);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [params.claimId]);

  if (loading) return <p className="text-sm text-muted-foreground">Loading claim…</p>;
  if (error || !claim) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-destructive">{error ?? "Claim not found."}</p>
        <Button variant="outline" className="w-fit" onClick={() => router.push("/queue")}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Back to queue
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" onClick={() => router.push("/queue")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="font-mono text-xl font-semibold">{claim.claim_id}</h1>
          <p className="text-sm text-muted-foreground">Submitted {formatDateTime(claim.created_at)}</p>
        </div>
        <div className="ml-auto"><DecisionBadge decision={claim.final_decision} /></div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Left: claim facts */}
        <Card className="lg:col-span-2 h-fit">
          <CardHeader>
            <CardTitle>Claim Facts</CardTitle>
            <CardDescription>Extracted by the Intake Agent</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <Fact label="Patient ID" value={claim.patient_id} />
              <Fact label="Provider ID" value={claim.provider_id ?? "—"} />
              <Fact label="Plan Type" value={claim.plan_type ?? "—"} />
              <Fact label="Treatment Date" value={formatDate(claim.treatment_date)} />
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <Fact label="ICD-10 Diagnosis" value={claim.icd10_codes.join(", ") || "—"} />
              <Fact label="CPT Procedure" value={claim.cpt_codes.join(", ") || "—"} />
              <Fact label="Billed Amount" value={formatAED(claim.billed_amount)} />
              <Fact label="Approved Amount" value={formatAED(claim.approved_amount)} />
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <Fact
                label="Prior Auth Required"
                value={claim.prior_auth_required === null ? "—" : claim.prior_auth_required ? "Yes" : "No"}
              />
              <Fact
                label="Prior Auth Obtained"
                value={claim.prior_auth_obtained === null ? "—" : claim.prior_auth_obtained ? "Yes" : "No"}
              />
            </div>
            <Separator />
            <div className="flex flex-col gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">Coding Flags</span>
              <div className="flex flex-wrap gap-1.5">
                {claim.coding_flags.length === 0 && <span className="text-sm text-muted-foreground">None</span>}
                {claim.coding_flags.map((flag) => (
                  <Badge key={flag} variant="warning">{flag.replaceAll("_", " ")}</Badge>
                ))}
              </div>
            </div>
            <Separator />
            <div className="flex flex-col gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">Fraud Score</span>
              <FraudScoreMeter score={claim.fraud_score} />
              {claim.fraud_top_features.length > 0 && (
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {claim.fraud_top_features.map((f) => (
                    <li key={f.feature} className="flex justify-between">
                      <span>{f.feature.replaceAll("_", " ")}</span>
                      <span className={f.contribution >= 0 ? "text-destructive" : "text-success"}>
                        {f.contribution >= 0 ? "+" : ""}{f.contribution.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right: decision trace + policy grounding */}
        <div className="flex flex-col gap-6 lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>Decision & Rationale</CardTitle>
              <CardDescription>Every recommendation is grounded in a cited policy clause — never a bare verdict.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm text-muted-foreground">RAG recommendation:</span>
                <RecommendationBadge recommendation={claim.decision_recommendation} />
                <span className="text-sm text-muted-foreground">→ Router final decision:</span>
                <DecisionBadge decision={claim.final_decision} />
              </div>
              {claim.decision_rationale && (
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm leading-relaxed">
                  {claim.decision_rationale}
                </div>
              )}
              {claim.escalation_reason && (
                <div className="rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm leading-relaxed text-warning">
                  <strong>Escalation reason:</strong> {claim.escalation_reason}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Agent-by-Agent Trace</CardTitle>
              <CardDescription>Intake → Coding → Fraud Scoring → Policy RAG → Decision Router</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="timeline">
                <TabsList>
                  <TabsTrigger value="timeline">Timeline</TabsTrigger>
                  <TabsTrigger value="clauses">Retrieved Clauses ({claim.retrieved_clauses.length})</TabsTrigger>
                </TabsList>
                <TabsContent value="timeline">
                  {trace.length > 0 ? (
                    <TraceTimeline steps={trace} />
                  ) : (
                    <p className="text-sm text-muted-foreground">No agent trace recorded for this claim.</p>
                  )}
                </TabsContent>
                <TabsContent value="clauses">
                  <div className="flex flex-col gap-3">
                    {claim.retrieved_clauses.length === 0 && (
                      <p className="text-sm text-muted-foreground">No clauses were retrieved for this claim.</p>
                    )}
                    {claim.retrieved_clauses.map((clause) => (
                      <ClauseCard key={clause.clause_id} clause={clause} />
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
