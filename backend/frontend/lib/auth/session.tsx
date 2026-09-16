"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { type User, UserSchema } from "@/lib/types";
import { tokenStore } from "@/lib/api/client";

// ─── Session Types ────────────────────────────────────────────────────────────

interface KnowraSession {
  user: User;
  accessToken: string;
  tenantId: string;
}

interface AuthContextValue {
  session: KnowraSession | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "knowra_session";

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<KnowraSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Rehydrate session from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      const accessToken = tokenStore.getAccessToken();
      if (raw && accessToken) {
        const parsed = JSON.parse(raw);
        const user = UserSchema.parse(parsed.user);
        setSession({ user, accessToken, tenantId: user.tenant_id });
        if (typeof document !== "undefined") {
          document.cookie = `knowra_access_token=${encodeURIComponent(accessToken)}; path=/; max-age=604800; SameSite=Lax`;
        }
      } else {
        tokenStore.clearTokens();
        setSession(null);
      }
    } catch {
      tokenStore.clearTokens();
      setSession(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(
    (accessToken: string, refreshToken: string, user: User) => {
      tokenStore.setTokens(accessToken, refreshToken);
      const newSession: KnowraSession = {
        user,
        accessToken,
        tenantId: user.tenant_id,
      };
      localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ user, tenantId: user.tenant_id })
      );
      setSession(newSession);
    },
    []
  );

  const logout = useCallback(() => {
    tokenStore.clearTokens();
    setSession(null);
    window.location.href = "/login";
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isLoading,
      isAuthenticated: session !== null,
      login,
      logout,
    }),
    [session, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useSession(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useSession must be used within AuthProvider");
  return ctx;
}

export function useRequireAuth(): KnowraSession {
  const { session, isLoading } = useSession();

  useEffect(() => {
    if (!isLoading && !session) {
      window.location.href = "/login";
    }
  }, [session, isLoading]);

  return session as KnowraSession;
}
