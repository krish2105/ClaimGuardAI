"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, UserCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";

export function UserMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  if (loading) {
    return <div className="h-9 w-24" />;
  }

  if (!user) {
    return (
      <Button asChild variant="outline" size="sm">
        <Link href="/login">Log in</Link>
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={user.role === "admin" ? "warning" : "outline"} className="hidden sm:inline-flex">
        <UserCircle className="mr-1 h-3 w-3" />
        {user.username} · {user.role}
      </Badge>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Log out"
        onClick={() => {
          logout();
          router.push("/queue");
        }}
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  );
}
