import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/lib/auth-context";
import { NavBar } from "@/components/nav-bar";

export const metadata: Metadata = {
  title: "ClaimGuard AI — Claims Triage & Prior-Auth Assistant",
  description:
    "Agentic health insurance claims triage & prior-authorization RAG assistant for the UAE market. Portfolio demo — synthetic data only.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>
            <NavBar />
            <main className="container py-8">{children}</main>
            <footer className="container py-8 text-center text-xs text-muted-foreground">
              ClaimGuard AI is a portfolio demonstration built on entirely synthetic data.
              Not for production or real patient use.
            </footer>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
