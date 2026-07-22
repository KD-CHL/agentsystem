import { createContext, useContext, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router-dom";

import { LoginPage } from "../pages/LoginPage";
import { api, ApiError, setToken } from "../lib/api";
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
  const authError = sessionQuery.error;
  if (signedOut || authError) {
    // 401 means the backend is up but we're not signed in. Any other failure
    // (404 on the static demo, network error) means the backend is unreachable.
    const backendUnreachable = Boolean(authError) && !(authError instanceof ApiError && authError.status === 401);
    return <LoginPage onSignedIn={finishLogin} backendUnreachable={backendUnreachable} />;
  }
  if (!sessionQuery.data) {
    return <AuthLoading />;
  }

  const session = sessionQuery.data;
  const value: AuthContextValue = {
    session,
    can: (permission) => rolePermissions[session.user.role].has(permission),
    logout: async () => {
      await api.logout();
      setToken(null);
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

function AuthLoading() {
  return (
    <div style={{ display: "grid", minHeight: "100dvh", placeItems: "center", background: "var(--bg)", color: "var(--text-muted)" }}>
      <span>Checking session...</span>
    </div>
  );
}
