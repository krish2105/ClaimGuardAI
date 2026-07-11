"use client";

import * as React from "react";
import { ClipboardList, Stethoscope, ShieldAlert, ScrollText, Route, CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceStep } from "@/lib/types";

const AGENT_META: Record<string, { label: string; icon: React.ElementType }> = {
  intake: { label: "Intake Agent", icon: ClipboardList },
  coding: { label: "Coding Agent", icon: Stethoscope },
  fraud_scoring: { label: "Fraud Scoring Agent", icon: ShieldAlert },
  policy_rag: { label: "Policy RAG Agent", icon: ScrollText },
  decision_router: { label: "Decision Router", icon: Route },
};

export function TraceTimeline({
  steps,
  liveAgent,
}: {
  steps: TraceStep[];
  /** agent name currently "thinking" — shows a pulsing indicator, used by the live panel */
  liveAgent?: string | null;
}) {
  return (
    <ol className="space-y-0">
      {steps.map((step, i) => {
        const meta = AGENT_META[step.agent] ?? { label: step.agent, icon: ClipboardList };
        const Icon = meta.icon;
        const isLast = i === steps.length - 1;
        return (
          <li key={`${step.agent}-${i}`} className="relative flex gap-4 pb-8 last:pb-0 animate-slide-up">
            {!isLast && (
              <span className="absolute left-[19px] top-10 h-full w-px bg-border" aria-hidden />
            )}
            <span
              className={cn(
                "z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2",
                step.status === "failed"
                  ? "border-destructive bg-destructive/10 text-destructive"
                  : "border-primary bg-primary/10 text-primary"
              )}
            >
              <Icon className="h-4.5 w-4.5" />
            </span>
            <div className="flex-1 pt-1.5">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm">{meta.label}</span>
                {step.duration_ms !== null && step.duration_ms !== undefined && (
                  <span className="text-xs text-muted-foreground">{step.duration_ms.toFixed(0)} ms</span>
                )}
              </div>
              <p className="mt-0.5 text-sm text-muted-foreground">{step.summary}</p>
            </div>
          </li>
        );
      })}
      {liveAgent && (
        <li className="flex gap-4 animate-fade-in">
          <span className="z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-primary bg-primary/10 text-primary">
            <Loader2 className="h-4.5 w-4.5 animate-spin" />
          </span>
          <div className="flex-1 pt-1.5">
            <span className="font-semibold text-sm">{AGENT_META[liveAgent]?.label ?? liveAgent}</span>
            <p className="mt-0.5 text-sm text-muted-foreground">Thinking…</p>
          </div>
        </li>
      )}
      {!liveAgent && steps.length > 0 && (
        <li className="flex items-center gap-2 pt-1 text-sm text-success">
          <CheckCircle2 className="h-4 w-4" /> Decision trace complete
        </li>
      )}
    </ol>
  );
}
