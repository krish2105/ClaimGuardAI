"use client";

import * as React from "react";
import { login as apiLogin, getMe, setAuthToken } from "@/lib/api";

export type Role = "adjuster" | "admin";
export type AuthUser = { username: string; role: Role };

const TOKEN_STORAGE_KEY = "claimguard-token";

const AuthContext = React.createContext<{
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
} | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    // Re-validate against the backend on every load rather than trusting a
    // locally cached role — this is what makes the role real (server-derived)
    // instead of a client-side label, and it naturally handles an expired
    // token by falling back to logged-out.
    setAuthToken(token);
    getMe()
      .then((me) => setUser(me))
      .catch(() => {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        setAuthToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = React.useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    window.localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
    setAuthToken(res.access_token);
    setUser({ username: res.username, role: res.role });
  }, []);

  const logout = React.useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
