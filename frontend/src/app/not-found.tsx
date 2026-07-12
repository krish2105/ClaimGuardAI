import Link from "next/link";
import { FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <FileSearch className="h-10 w-10 text-muted-foreground" />
      <div>
        <h1 className="text-lg font-semibold">Page not found</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          There&apos;s nothing at this address. Try the claims queue instead.
        </p>
      </div>
      <Button asChild>
        <Link href="/queue">Back to queue</Link>
      </Button>
    </div>
  );
}
