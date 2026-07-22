import { createContext, useContext, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router-dom";

import { LoginPage } from "../pages/LoginPage";
import { api, ApiError } from "../lib/api";
import type { AuthSession, Permission, UserRole } from "../types";

const rolePermissions: Record<UserRole, ReadonlySet<Permission>> = {
  admin: new Set<Permission>([
    "task:read", "task:write", "task:chat", "approval:decide", "project:read", "project:write",
    "agent:read", "agent:manage", "credential:manage", "operations:read", "audit:read", "user:manage",
  ]),
  operator: new Set<Permission>([
    "task:read", "task:write", "task:chat", "approval:decide", "project:read", "project:write",
    "agent:read", "operations:read", "audit:read",
  ]),
  reviewer: new Set<Permission>([
    "task:read", "task:chat", "approval:decide", "project:read", "agent:read", "operations:read", "audit:read",
  ]),
  viewer: new Set<Permission>(["task:read", "project:read", "agent:read"]),
};

interface AuthContextValue {
  session: AuthSession;
  can: (permission: Permission) => boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthBoundary() {
  const queryClient = useQueryClient();
  const [signedOut, setSignedOut] = useState(false);
  const sessionQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.me,
    retry: false,
  });

  const finishLogin = (session: AuthSession) => {
    setSignedOut(false);
    queryClient.setQueryData(["auth", "me"], session);
  };

  if (sessionQuery.isLoading) return <AuthLoading />;
  if (signedOut || (sessionQuery.error instanceof ApiError && sessionQuery.error.status === 401)) {
    return <LoginPage onSignedIn={finishLogin} />;
  }
  if (!sessionQuery.data) {
    return <AuthLoading error={sessionQuery.error instanceof Error ? sessionQuery.error.message : undefined} />;
  }

  const session = sessionQuery.data;
  const value: AuthContextValue = {
    session,
    can: (permission) => rolePermissions[session.user.role].has(permission),
    logout: async () => {
      await api.logout();
      setSignedOut(true);
      queryClient.removeQueries();
    },
  };
  return <AuthContext.Provider value={value}><Outlet /></AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthBoundary");
  return context;
}

export function PermissionRoute({ permission, children }: { permission: Permission; children: ReactNode }) {
  const { can } = useAuth();
  return can(permission) ? children : <Navigate to="/" replace />;
}

function AuthLoading({ error }: { error?: string }) {
  return (
    <div style={{ display: "grid", minHeight: "100dvh", placeItems: "center", background: "var(--bg)", color: "var(--text-muted)" }}>
      <span>{error ?? "Checking session..."}</span>
    </div>
  );
}
