"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, LogIn } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/error-state";
import { useAuth } from "@/lib/auth-context";

const DEMO_ACCOUNTS = [
  { username: "adjuster", password: "adjuster123", role: "Adjuster" },
  { username: "admin", password: "admin123", role: "Admin" },
];

export default function LoginPage() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (user) router.replace("/queue");
  }, [user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      router.replace("/queue");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="flex flex-col items-center gap-2 text-center">
        <ShieldCheck className="h-8 w-8 text-primary" />
        <h1 className="text-xl font-semibold">Sign in to ClaimGuard AI</h1>
        <p className="text-sm text-muted-foreground">
          Escalation resolution and the Admin Panel require a logged-in adjuster or admin account.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Log in</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="username">Username</Label>
              <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <ErrorState message={error} />}
            <Button type="submit" disabled={submitting}>
              <LogIn className="mr-1.5 h-4 w-4" />
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Demo credentials</CardTitle>
          <CardDescription>
            This is a portfolio demo on entirely synthetic data — these accounts are intentionally public.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {DEMO_ACCOUNTS.map((acct) => (
            <button
              key={acct.username}
              type="button"
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-accent"
              onClick={() => {
                setUsername(acct.username);
                setPassword(acct.password);
              }}
            >
              <span>
                <span className="font-medium">{acct.role}</span>
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {acct.username} / {acct.password}
                </span>
              </span>
              <span className="text-xs text-primary">Use</span>
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
