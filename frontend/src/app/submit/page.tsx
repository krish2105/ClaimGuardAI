"use client";

import * as React from "react";
import Link from "next/link";
import { Sparkles, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TraceTimeline } from "@/components/trace-timeline";
import { DecisionBadge } from "@/components/status-badge";
import { ErrorState } from "@/components/error-state";
import { submitClaim, WS_BASE_URL } from "@/lib/api";
import type { PlanType, StreamMessage, TraceStep, FinalDecision } from "@/lib/types";

const SAMPLE_PRESETS = [
  {
    label: "Routine — should auto-approve",
    patient_id: "PAT-2001", provider_id: "PRV-004", plan_type: "Enhanced" as PlanType,
    icd10_codes: "I10", cpt_codes: "93000", billed_amount: "220",
  },
  {
    label: "Suspicious — diagnosis/procedure mismatch",
    patient_id: "PAT-2002", provider_id: "PRV-017", plan_type: "Basic" as PlanType,
    icd10_codes: "M54.5", cpt_codes: "87880", billed_amount: "180",
  },
  {
    label: "High-value — advanced imaging",
    patient_id: "PAT-2003", provider_id: "PRV-009", plan_type: "Comprehensive" as PlanType,
    icd10_codes: "M17.9", cpt_codes: "72148", billed_amount: "3600",
  },
];

export default function SubmitPage() {
  const [form, setForm] = React.useState({
    patient_id: "PAT-2001",
    provider_id: "PRV-004",
    plan_type: "Enhanced" as PlanType,
    treatment_date: new Date().toISOString().slice(0, 10),
    icd10_codes: "I10",
    cpt_codes: "93000",
    billed_amount: "220",
    notes: "",
  });
  const [submitting, setSubmitting] = React.useState(false);
  const [claimId, setClaimId] = React.useState<string | null>(null);
  const [steps, setSteps] = React.useState<TraceStep[]>([]);
  const [liveAgent, setLiveAgent] = React.useState<string | null>(null);
  const [finalDecision, setFinalDecision] = React.useState<FinalDecision | null>(null);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const wsRef = React.useRef<WebSocket | null>(null);

  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  function applyPreset(preset: (typeof SAMPLE_PRESETS)[number]) {
    setForm((f) => ({
      ...f,
      patient_id: preset.patient_id,
      provider_id: preset.provider_id,
      plan_type: preset.plan_type,
      icd10_codes: preset.icd10_codes,
      cpt_codes: preset.cpt_codes,
      billed_amount: preset.billed_amount,
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setSteps([]);
    setFinalDecision(null);
    setLiveAgent("intake");

    try {
      const res = await submitClaim({
        patient_id: form.patient_id,
        provider_id: form.provider_id,
        plan_type: form.plan_type,
        treatment_date: form.treatment_date,
        icd10_codes: form.icd10_codes.split(",").map((c) => c.trim()).filter(Boolean),
        cpt_codes: form.cpt_codes.split(",").map((c) => c.trim()).filter(Boolean),
        billed_amount: parseFloat(form.billed_amount),
        notes: form.notes || undefined,
      });
      setClaimId(res.claim_id);

      const ws = new WebSocket(`${WS_BASE_URL}${res.ws_url}`);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        const msg: StreamMessage = JSON.parse(event.data);
        if (msg.type === "step") {
          const state = msg.state as { agent_trace?: TraceStep[] } | undefined;
          if (state?.agent_trace) setSteps(state.agent_trace);
          const AGENT_ORDER = ["intake", "coding", "fraud_scoring", "policy_rag", "decision_router"];
          const idx = AGENT_ORDER.indexOf(msg.agent ?? "");
          setLiveAgent(idx >= 0 && idx < AGENT_ORDER.length - 1 ? AGENT_ORDER[idx + 1] : null);
        } else if (msg.type === "final") {
          setFinalDecision(msg.final_decision ?? null);
        } else if (msg.type === "done") {
          setLiveAgent(null);
          setSubmitting(false);
          ws.close();
        }
      };
      ws.onerror = () => {
        setSubmitError("Lost connection to the live agent trace. The claim may still be processing — check the queue in a moment.");
        setSubmitting(false);
        setLiveAgent(null);
      };
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit the claim. Please try again.");
      setSubmitting(false);
      setLiveAgent(null);
    }
  }

  React.useEffect(() => () => wsRef.current?.close(), []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Submit a Claim</h1>
        <p className="text-sm text-muted-foreground">
          Watch the 5-agent pipeline think in real time — Intake → Coding → Fraud Scoring → Policy RAG → Decision Router.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2 h-fit">
          <CardHeader>
            <CardTitle>Claim Details</CardTitle>
            <CardDescription>Or start from a sample scenario below.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex flex-wrap gap-2">
              {SAMPLE_PRESETS.map((preset) => (
                <Button key={preset.label} type="button" variant="secondary" size="sm" onClick={() => applyPreset(preset)}>
                  <Sparkles className="mr-1 h-3.5 w-3.5" /> {preset.label}
                </Button>
              ))}
            </div>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="patient_id">Patient ID</Label>
                  <Input id="patient_id" value={form.patient_id} onChange={(e) => set("patient_id")(e.target.value)} required />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="provider_id">Provider ID</Label>
                  <Input id="provider_id" value={form.provider_id} onChange={(e) => set("provider_id")(e.target.value)} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label>Plan Type</Label>
                  <Select value={form.plan_type} onValueChange={(v) => set("plan_type")(v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {(["Basic", "Enhanced", "Thiqa", "Comprehensive"] as PlanType[]).map((p) => (
                        <SelectItem key={p} value={p}>{p}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="treatment_date">Treatment Date</Label>
                  <Input id="treatment_date" type="date" value={form.treatment_date} onChange={(e) => set("treatment_date")(e.target.value)} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="icd10">ICD-10 Codes</Label>
                  <Input id="icd10" value={form.icd10_codes} onChange={(e) => set("icd10_codes")(e.target.value)} placeholder="I10, E11.9" required />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="cpt">CPT Codes</Label>
                  <Input id="cpt" value={form.cpt_codes} onChange={(e) => set("cpt_codes")(e.target.value)} placeholder="93000" required />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="billed">Billed Amount (AED)</Label>
                <Input id="billed" type="number" step="0.01" value={form.billed_amount} onChange={(e) => set("billed_amount")(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea id="notes" value={form.notes} onChange={(e) => set("notes")(e.target.value)} rows={2} />
              </div>
              <Button type="submit" disabled={submitting} className="mt-2">
                <Send className="mr-1.5 h-4 w-4" />
                {submitting ? "Processing…" : "Submit Claim"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 h-fit">
          <CardHeader>
            <CardTitle>Live Agent Trace</CardTitle>
            <CardDescription>
              {claimId ? (
                <>Claim <span className="font-mono text-primary">{claimId}</span></>
              ) : (
                "Submit a claim to watch the pipeline reason step by step."
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {submitError && (
              <ErrorState
                message={submitError}
                onRetry={() => setSubmitError(null)}
              />
            )}
            {!submitError && steps.length === 0 && !submitting && (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                No claim submitted yet.
              </div>
            )}
            {!submitError && (steps.length > 0 || submitting) && <TraceTimeline steps={steps} liveAgent={liveAgent} />}
            {finalDecision && claimId && (
              <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-muted/40 p-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Final decision:</span>
                  <DecisionBadge decision={finalDecision} />
                </div>
                <Link href={`/claims/${claimId}`} className="text-sm font-medium text-primary hover:underline">
                  View full claim →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
