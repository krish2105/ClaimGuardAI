"use client";

import * as React from "react";
import { useRole, type Role } from "@/lib/role-context";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ROLE_LABELS: Record<Role, string> = {
  adjuster: "Adjuster",
  admin: "Admin",
};

export function RoleSwitcher() {
  const { role, setRole } = useRole();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="h-9 w-[168px]" />;
  }

  return (
    <Select value={role} onValueChange={(v) => setRole(v as Role)}>
      <SelectTrigger className="h-9 w-[168px] whitespace-nowrap text-xs">
        <span className="whitespace-nowrap text-muted-foreground">Viewing as:&nbsp;</span>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
          <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
