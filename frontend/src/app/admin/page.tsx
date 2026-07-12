"use client";

import * as React from "react";
import Link from "next/link";
import { ShieldCheck, ShieldAlert, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";
import { runAdminSeedStep, type AdminSeedStep } from "@/lib/api";

const TOKEN_STORAGE_KEY = "claimguard-admin-token";

const STEPS: { key: AdminSeedStep; label: string; description: string }[] = [
  { key: "dataset", label: "1. Generate Dataset", description: "Creates the synthetic UAE-style claims CSVs." },
  { key: "database", label: "2. Seed Database", description: "Loads providers, claims, and reference data into Postgres." },
  { key: "policies", label: "3. Ingest Policies", description: "Embeds the policy corpus into the Qdrant index." },
  { key: "model", label: "4. Train Fraud Model", description: "Fits the XGBoost fraud scoring model on the seeded claims." },
  { key: "users", label: "5. Seed Demo Users", description: "Creates the adjuster/admin demo login accounts." },
  { key: "batch", label: "6. Run Batch Pipeline", description: "Runs every seeded claim through the 5-agent pipeline." },
];

type StepStatus = { state: "idle" | "running" | "done" | "error"; message?: string };

export default function AdminPage() {
  const { user, loading } = useAuth();
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

  const isAdmin = user?.role === "admin";

  async function runStep(step: AdminSeedStep) {
    setStatuses((s) => ({ ...s, [step]: { state: "running" } }));
    try {
      // A logged-in admin's JWT is attached automatically by apiFetch; the
      // token here only matters when nobody is logged in yet (first-ever
      // bootstrap of a fresh deployment, before any user account exists).
      await runAdminSeedStep(step, isAdmin ? undefined : token);
      setStatuses((s) => ({ ...s, [step]: { state: "done" } }));
    } catch (err) {
      setStatuses((s) => ({
        ...s,
        [step]: { state: "error", message: err instanceof Error ? err.message : "Step failed." },
      }));
    }
  }

  if (!mounted || loading) return null;

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

      {isAdmin ? (
        <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm text-success">
          <ShieldCheck className="h-4 w-4 shrink-0" />
          Authenticated as <span className="font-medium">{user.username}</span> (admin) — no token needed below.
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          Not logged in as admin.{" "}
          <Link href="/login" className="font-medium underline underline-offset-2">Log in</Link>, or paste the
          bootstrap token below (needed the first time, before any admin account exists).
        </div>
      )}

      {!isAdmin && (
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
      )}

      <Card>
        <CardHeader>
          <CardTitle>Bootstrap Steps</CardTitle>
          <CardDescription>Disabled on the backend (fails closed) unless you&apos;re an authenticated admin or supply the token.</CardDescription>
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
                    disabled={(!isAdmin && !token) || status.state === "running"}
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
