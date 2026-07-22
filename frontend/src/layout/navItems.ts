import {
  Activity,
  Bot,
  Cable,
  FolderGit2,
  LayoutDashboard,
  Settings,
  Shield,
  UsersRound,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import type { Permission } from "../types";

export interface NavItem {
  to: string;
  icon: LucideIcon;
  key: string;
  permission?: Permission;
  end?: boolean;
}

export const navItems: NavItem[] = [
  { to: "/", icon: LayoutDashboard, key: "workbench", permission: "task:read", end: true },
  { to: "/tasks", icon: Workflow, key: "tasks", permission: "task:read" },
  { to: "/projects", icon: FolderGit2, key: "projects", permission: "project:read" },
  { to: "/agents", icon: Bot, key: "agents", permission: "agent:manage" },
  { to: "/capabilities", icon: Cable, key: "capabilities", permission: "agent:manage" },
  { to: "/operations", icon: Activity, key: "operations", permission: "operations:read" },
  { to: "/approvals", icon: Shield, key: "approvals", permission: "approval:decide" },
  { to: "/users", icon: UsersRound, key: "users", permission: "user:manage" },
  { to: "/settings", icon: Settings, key: "settings" },
];
