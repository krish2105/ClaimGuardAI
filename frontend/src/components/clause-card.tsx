import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { RetrievedClause } from "@/lib/types";

export function ClauseCard({ clause, cited }: { clause: RetrievedClause; cited?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        cited ? "border-primary/40 bg-primary/5" : "border-border bg-background"
      )}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-primary" />
          <span className="font-mono text-xs font-semibold text-primary">{clause.clause_id}</span>
          {cited && <Badge variant="default" className="text-[10px]">Cited</Badge>}
        </div>
        <span className="text-xs text-muted-foreground">
          {clause.source_doc} · similarity {clause.similarity.toFixed(2)}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-foreground/90">{clause.text}</p>
    </div>
  );
}
