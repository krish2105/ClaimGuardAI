"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { listClaims } from "@/lib/api";
import type { ClaimListItem } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { DecisionBadge, RecommendationBadge } from "@/components/status-badge";
import { FraudScoreMeter } from "@/components/fraud-score-meter";
import { ErrorState } from "@/components/error-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatAED, formatDate } from "@/lib/utils";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "auto_approved", label: "Auto-Approved" },
  { value: "auto_denied", label: "Auto-Denied" },
  { value: "escalated", label: "Escalated" },
];

const PLAN_OPTIONS = [
  { value: "all", label: "All plans" },
  { value: "Basic", label: "Basic" },
  { value: "Enhanced", label: "Enhanced" },
  { value: "Thiqa", label: "Thiqa" },
  { value: "Comprehensive", label: "Comprehensive" },
];

export default function QueuePage() {
  const router = useRouter();
  const [items, setItems] = React.useState<ClaimListItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [status, setStatus] = React.useState("all");
  const [planType, setPlanType] = React.useState("all");
  const [search, setSearch] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(() => {
    setLoading(true);
    setError(null);
    listClaims({
      status: status === "all" ? undefined : status,
      plan_type: planType === "all" ? undefined : planType,
      limit: 100,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [status, planType]);

  React.useEffect(() => {
    load();
  }, [load]);

  const filtered = items.filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      item.claim_id.toLowerCase().includes(q) ||
      item.patient_id.toLowerCase().includes(q) ||
      (item.provider_id ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Claims Queue</h1>
        <p className="text-sm text-muted-foreground">
          {total} claims processed by the 5-agent pipeline. Every decision cites the policy clause behind it.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <CardTitle>Filter</CardTitle>
            <CardDescription>Narrow the queue by decision status or plan tier.</CardDescription>
          </div>
          <div className="flex flex-1 flex-wrap items-center gap-2 sm:justify-end">
            <div className="relative min-w-[180px] flex-1 sm:flex-none">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search claim/patient/provider…"
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-[160px]"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={planType} onValueChange={setPlanType}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Plan" /></SelectTrigger>
              <SelectContent>
                {PLAN_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={load}>Refresh</Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && <ErrorState message={error} onRetry={load} />}
          {!error && loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading claims…</p>}
          {!error && !loading && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Claim ID</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Treatment Date</TableHead>
                  <TableHead>Billed Amount</TableHead>
                  <TableHead>Fraud Score</TableHead>
                  <TableHead>RAG Recommendation</TableHead>
                  <TableHead>Final Decision</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((claim) => (
                  <TableRow
                    key={claim.claim_id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/claims/${claim.claim_id}`)}
                  >
                    <TableCell>
                      <Link href={`/claims/${claim.claim_id}`} className="font-mono text-xs font-medium text-primary hover:underline">
                        {claim.claim_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{claim.patient_id}</TableCell>
                    <TableCell className="text-sm">{claim.plan_type ?? "—"}</TableCell>
                    <TableCell className="text-sm">{formatDate(claim.treatment_date)}</TableCell>
                    <TableCell className="text-sm tabular-nums">{formatAED(claim.billed_amount)}</TableCell>
                    <TableCell><FraudScoreMeter score={claim.fraud_score} showLabel={false} /></TableCell>
                    <TableCell><RecommendationBadge recommendation={claim.decision_recommendation} /></TableCell>
                    <TableCell><DecisionBadge decision={claim.final_decision} /></TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                      No claims match the current filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
