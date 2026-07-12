"use client";

import * as React from "react";
import Link from "next/link";
import { AlertTriangle, Check, X, LogIn } from "lucide-react";
import { listEscalations, resolveEscalation } from "@/lib/api";
import type { EscalationItem } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FraudScoreMeter } from "@/components/fraud-score-meter";
import { ErrorState } from "@/components/error-state";
import { useAuth } from "@/lib/auth-context";
import { formatAED, formatDateTime } from "@/lib/utils";

function EscalationCard({ item, onResolved }: { item: EscalationItem; onResolved: () => void }) {
  const { user } = useAuth();
  const canResolve = user?.role === "adjuster" || user?.role === "admin";
  const [notes, setNotes] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function resolve(decision: "approve" | "deny") {
    setBusy(true);
    setError(null);
    try {
      await resolveEscalation(item.escalation_id, { adjuster_decision: decision, adjuster_notes: notes || undefined });
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve this escalation. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link href={`/claims/${item.claim_id}`} className="font-mono text-sm font-semibold text-primary hover:underline">
              {item.claim_id}
            </Link>
            <p className="mt-0.5 text-xs text-muted-foreground">Escalated {formatDateTime(item.created_at)}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline">{item.plan_type ?? "—"}</Badge>
            <span className="text-sm font-medium tabular-nums">{formatAED(item.billed_amount)}</span>
            <FraudScoreMeter score={item.fraud_score} showLabel={false} />
          </div>
        </div>

        {item.escalation_reason && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{item.escalation_reason}</span>
          </div>
        )}

        {item.status === "pending" ? (
          canResolve ? (
            <div className="flex flex-col gap-2">
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Textarea
                  placeholder="Adjuster notes (optional)"
                  className="sm:flex-1"
                  rows={1}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={busy} onClick={() => resolve("approve")}>
                    <Check className="mr-1 h-3.5 w-3.5" /> Approve
                  </Button>
                  <Button size="sm" variant="destructive" disabled={busy} onClick={() => resolve("deny")}>
                    <X className="mr-1 h-3.5 w-3.5" /> Deny
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
              <Link href="/login" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
                <LogIn className="h-3.5 w-3.5" /> Log in
              </Link>
              as an adjuster or admin to approve or deny this claim.
            </div>
          )
        ) : (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Resolved{item.resolved_by ? ` by ${item.resolved_by}` : ""}:</span>
            <Badge variant={item.adjuster_decision === "approve" ? "success" : "destructive"}>
              {item.adjuster_decision}
            </Badge>
            {item.adjuster_notes && <span className="text-muted-foreground">— {item.adjuster_notes}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function EscalationsPage() {
  const [tab, setTab] = React.useState<"pending" | "resolved">("pending");
  const [items, setItems] = React.useState<EscalationItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback((status: string) => {
    setLoading(true);
    setError(null);
    listEscalations(status)
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load escalations."))
      .finally(() => setLoading(false));
  }, []);

  React.useEffect(() => load(tab), [tab, load]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Escalation Queue</h1>
        <p className="text-sm text-muted-foreground">
          Claims the pipeline routed to a human adjuster — high fraud score, ungrounded policy retrieval, or a coding mismatch.
        </p>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "pending" | "resolved")}>
        <TabsList>
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="resolved">Resolved</TabsTrigger>
        </TabsList>
        <TabsContent value={tab}>
          {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
          {!loading && error && <ErrorState message={error} onRetry={() => load(tab)} />}
          {!loading && !error && items.length === 0 && (
            <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">
              No {tab} escalations.
            </CardContent></Card>
          )}
          {!loading && !error && (
            <div className="flex flex-col gap-4">
              {items.map((item) => (
                <EscalationCard key={item.escalation_id} item={item} onResolved={() => load(tab)} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
