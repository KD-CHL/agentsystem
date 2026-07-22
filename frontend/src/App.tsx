import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthBoundary, PermissionRoute } from "./auth/AuthContext";
import { AppShell } from "./layout/AppShell";

const AgentStudioPage = lazy(() => import("./pages/AgentStudioPage").then((module) => ({ default: module.AgentStudioPage })));
const CapabilitiesPage = lazy(() => import("./pages/CapabilitiesPage").then((module) => ({ default: module.CapabilitiesPage })));
const OperationsPage = lazy(() => import("./pages/OperationsPage").then((module) => ({ default: module.OperationsPage })));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage").then((module) => ({ default: module.ProjectsPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const UsersPage = lazy(() => import("./pages/UsersPage").then((module) => ({ default: module.UsersPage })));
const WorkbenchPage = lazy(() => import("./pages/WorkbenchPage").then((module) => ({ default: module.WorkbenchPage })));

export default function App() {
  return (
    <Routes>
      <Route element={<AuthBoundary />}>
        <Route element={<AppShell />}>
          <Route index element={<Page><WorkbenchPage /></Page>} />
          <Route path="tasks" element={<Page><WorkbenchPage /></Page>} />
          <Route path="tasks/:taskId" element={<Page><WorkbenchPage /></Page>} />
          <Route path="projects" element={<Page><ProjectsPage /></Page>} />
          <Route path="agents" element={<PermissionRoute permission="agent:manage"><Page><AgentStudioPage /></Page></PermissionRoute>} />
          <Route path="capabilities" element={<PermissionRoute permission="agent:manage"><Page><CapabilitiesPage /></Page></PermissionRoute>} />
          <Route path="operations" element={<PermissionRoute permission="operations:read"><Page><OperationsPage /></Page></PermissionRoute>} />
          <Route path="users" element={<PermissionRoute permission="user:manage"><Page><UsersPage /></Page></PermissionRoute>} />
          <Route path="settings" element={<Page><SettingsPage /></Page>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}

function Page({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div style={{ display: "grid", height: "100%", placeItems: "center", color: "var(--text-muted)" }}>Loading...</div>}>{children}</Suspense>;
}
