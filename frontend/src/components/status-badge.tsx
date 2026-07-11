import { CheckCircle2, XCircle, AlertTriangle, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { FinalDecision, Recommendation } from "@/lib/types";

export function DecisionBadge({ decision }: { decision: FinalDecision | null | undefined }) {
  switch (decision) {
    case "auto_approved":
      return (
        <Badge variant="success">
          <CheckCircle2 className="h-3 w-3" /> Auto-Approved
        </Badge>
      );
    case "auto_denied":
      return (
        <Badge variant="destructive">
          <XCircle className="h-3 w-3" /> Auto-Denied
        </Badge>
      );
    case "escalated":
      return (
        <Badge variant="warning">
          <AlertTriangle className="h-3 w-3" /> Escalated
        </Badge>
      );
    default:
      return (
        <Badge variant="muted">
          <HelpCircle className="h-3 w-3" /> Processing
        </Badge>
      );
  }
}

export function RecommendationBadge({ recommendation }: { recommendation: Recommendation | null | undefined }) {
  if (!recommendation) return <Badge variant="muted">—</Badge>;
  const map: Record<Recommendation, { label: string; variant: "success" | "destructive" | "warning" }> = {
    approve: { label: "Approve", variant: "success" },
    deny: { label: "Deny", variant: "destructive" },
    escalate: { label: "Escalate", variant: "warning" },
  };
  const cfg = map[recommendation];
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}
