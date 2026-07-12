"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";
import { getFraudTrends } from "@/lib/api";
import type { FraudTrendsResponse } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ErrorState } from "@/components/error-state";
import { STATUS_COLORS, CATEGORICAL, SEQUENTIAL_BLUE, CHART_CHROME } from "@/lib/chart-colors";

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const { resolvedTheme } = useTheme();
  const mode = resolvedTheme === "dark" ? "dark" : "light";
  const status = STATUS_COLORS[mode];
  const categorical = CATEGORICAL[mode];
  const blues = SEQUENTIAL_BLUE[mode];
  const chrome = CHART_CHROME[mode];

  const [data, setData] = React.useState<FraudTrendsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getFraudTrends()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load analytics."))
      .finally(() => setLoading(false));
  }, []);

  React.useEffect(() => load(), [load]);

  if (loading) return <p className="text-sm text-muted-foreground">Loading analytics…</p>;
  if (error || !data) return <ErrorState message={error ?? "Failed to load analytics."} onRetry={load} />;

  if (data.total_claims_processed === 0) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        </div>
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No claims processed yet. Submit a claim from the{" "}
            <a href="/submit" className="font-medium text-primary hover:underline">Submit</a> page to see trends here.
          </CardContent>
        </Card>
      </div>
    );
  }

  const planData = Object.entries(data.plan_type_breakdown).map(([plan, count]) => ({ plan, count }));
  const codingData = data.coding_flag_frequency.map((f) => ({ flag: f.flag.replaceAll("_", " "), count: f.count }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Escalation rate is tracked as a business KPI — too high means the pipeline isn&apos;t confident enough; too low risks missed fraud.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile label="Claims Processed" value={data.total_claims_processed.toLocaleString()} />
        <StatTile label="Escalation Rate" value={`${(data.escalation_rate * 100).toFixed(1)}%`} />
        <StatTile
          label="Top Coding Flag"
          value={codingData[0]?.flag ?? "None"}
          sub={codingData[0] ? `${codingData[0].count} claims` : undefined}
        />
        <StatTile
          label="Plan Tiers Active"
          value={String(planData.length)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Claim Volume & Outcome by Month</CardTitle>
          <CardDescription>Auto-approved, auto-denied, and escalated claim counts per treatment month.</CardDescription>
        </CardHeader>
        <CardContent className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.trend} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke={chrome.grid} vertical={false} />
              <XAxis dataKey="period" tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={{ stroke: chrome.axis }} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={false} tickLine={false} width={32} />
              <Tooltip
                contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 13 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="auto_approved" name="Auto-Approved" stackId="a" fill={status.good} radius={[0, 0, 0, 0]} />
              <Bar dataKey="auto_denied" name="Auto-Denied" stackId="a" fill={status.critical} />
              <Bar dataKey="escalated" name="Escalated" stackId="a" fill={status.warning} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Coding Flag Frequency</CardTitle>
            <CardDescription>How often the Coding Agent raised each integrity flag.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            {codingData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No coding flags raised.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={codingData} layout="vertical" margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke={chrome.grid} horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={false} tickLine={false} />
                  <YAxis
                    dataKey="flag" type="category" width={170}
                    tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={false} tickLine={false}
                  />
                  <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 13 }} />
                  <Bar dataKey="count" name="Claims flagged" fill={blues[3]} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Plan Type Mix</CardTitle>
            <CardDescription>Claim distribution across the four UAE-style plan tiers.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={planData} layout="vertical" margin={{ left: 0, right: 24, top: 8, bottom: 0 }}>
                <CartesianGrid stroke={chrome.grid} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="plan" type="category" width={110}
                  tick={{ fontSize: 12, fill: chrome.mutedText }} axisLine={false} tickLine={false}
                />
                <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 13 }} />
                <Bar dataKey="count" name="Claims" radius={[0, 4, 4, 0]}>
                  {planData.map((entry, i) => (
                    <Cell key={entry.plan} fill={categorical[i % categorical.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
