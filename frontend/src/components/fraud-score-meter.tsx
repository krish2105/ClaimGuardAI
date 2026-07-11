import { cn } from "@/lib/utils";

function scoreTier(score: number): { color: string; label: string } {
  if (score >= 75) return { color: "bg-destructive", label: "High risk" };
  if (score >= 40) return { color: "bg-warning", label: "Moderate risk" };
  return { color: "bg-success", label: "Low risk" };
}

export function FraudScoreMeter({ score, showLabel = true }: { score: number | null | undefined; showLabel?: boolean }) {
  if (score === null || score === undefined) {
    return <span className="text-sm text-muted-foreground">—</span>;
  }
  const { color, label } = scoreTier(score);
  return (
    <div className="flex min-w-[7rem] flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium tabular-nums">{score.toFixed(1)}/100</span>
        {showLabel && <span className="text-muted-foreground">{label}</span>}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}
