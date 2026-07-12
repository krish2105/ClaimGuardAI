"use client";

import * as React from "react";
import { ShieldAlert, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRole } from "@/lib/role-context";
import { runAdminSeedStep, type AdminSeedStep } from "@/lib/api";

const TOKEN_STORAGE_KEY = "claimguard-admin-token";

const STEPS: { key: AdminSeedStep; label: string; description: string }[] = [
  { key: "dataset", label: "1. Generate Dataset", description: "Creates the synthetic UAE-style claims CSVs." },
  { key: "database", label: "2. Seed Database", description: "Loads providers, claims, and reference data into Postgres." },
  { key: "policies", label: "3. Ingest Policies", description: "Embeds the policy corpus into the Qdrant index." },
  { key: "model", label: "4. Train Fraud Model", description: "Fits the XGBoost fraud scoring model on the seeded claims." },
  { key: "batch", label: "5. Run Batch Pipeline", description: "Runs every seeded claim through the 5-agent pipeline." },
];

type StepStatus = { state: "idle" | "running" | "done" | "error"; message?: string };

export default function AdminPage() {
  const { role } = useRole();
  const [mounted, setMounted] = React.useState(false);
  const [token, setToken] = React.useState("");
  const [statuses, setStatuses] = React.useState<Record<AdminSeedStep, StepStatus>>(
    Object.fromEntries(STEPS.map((s) => [s.key, { state: "idle" }])) as Record<AdminSeedStep, StepStatus>
  );

  React.useEffect(() => {
    setMounted(true);
    setToken(window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? "");
  }, []);

  function updateToken(value: string) {
    setToken(value);
    window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
  }

  async function runStep(step: AdminSeedStep) {
    setStatuses((s) => ({ ...s, [step]: { state: "running" } }));
    try {
      await runAdminSeedStep(step, token);
      setStatuses((s) => ({ ...s, [step]: { state: "done" } }));
    } catch (err) {
      setStatuses((s) => ({
        ...s,
        [step]: { state: "error", message: err instanceof Error ? err.message : "Step failed." },
      }));
    }
  }

  if (!mounted) return null;

  if (role !== "admin") {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
        <ShieldAlert className="h-8 w-8 text-muted-foreground" />
        <div>
          <h1 className="text-lg font-semibold">Admin Panel</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Switch &ldquo;Viewing as&rdquo; to Admin in the top nav to access data bootstrap tools.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Admin Panel</h1>
        <p className="text-sm text-muted-foreground">
          One-time data bootstrap for a fresh deployment — runs the same steps documented in{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">docs/DEPLOYMENT.md</code>, without a terminal.
          Run them in order; each is safe to retry on its own.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Admin Token</CardTitle>
          <CardDescription>
            Matches <code className="rounded bg-muted px-1 py-0.5 text-xs">ADMIN_SEED_TOKEN</code> on the backend.
            Stored only in this browser&apos;s local storage.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-1.5 sm:max-w-sm">
            <Label htmlFor="admin-token">X-Admin-Token</Label>
            <Input
              id="admin-token"
              type="password"
              value={token}
              onChange={(e) => updateToken(e.target.value)}
              placeholder="Paste your admin seed token"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bootstrap Steps</CardTitle>
          <CardDescription>Disabled on the backend (fails closed) unless a token is configured.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {STEPS.map((step) => {
            const status = statuses[step.key];
            return (
              <div
                key={step.key}
                className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-sm font-medium">{step.label}</p>
                  <p className="text-xs text-muted-foreground">{step.description}</p>
                  {status.state === "error" && (
                    <p className="mt-1 text-xs text-destructive">{status.message}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {status.state === "done" && <CheckCircle2 className="h-4 w-4 text-success" />}
                  {status.state === "error" && <XCircle className="h-4 w-4 text-destructive" />}
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!token || status.state === "running"}
                    onClick={() => runStep(step.key)}
                  >
                    {status.state === "running" && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                    {status.state === "running" ? "Running…" : status.state === "done" ? "Run again" : "Run"}
                  </Button>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
