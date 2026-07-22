import type { LucideIcon } from "lucide-react";
import { Binary, Braces, GitPullRequest, ListTree, Network, SearchCode, ShieldCheck, TestTube2 } from "lucide-react";

import type { AgentName } from "../types";

export const agentIcons: Record<AgentName, LucideIcon> = {
  orchestrator: Network,
  repo_context: SearchCode,
  planning: ListTree,
  coding: Braces,
  test: TestTube2,
  security: ShieldCheck,
  review: Binary,
  pr: GitPullRequest,
};

export const agentLabels: Record<AgentName, string> = {
  orchestrator: "Orchestrator",
  repo_context: "Repo Context",
  planning: "Planning",
  coding: "Coding",
  test: "Test",
  security: "Security",
  review: "Review",
  pr: "PR",
};

export const agentOrder: AgentName[] = [
  "orchestrator",
  "repo_context",
  "planning",
  "coding",
  "test",
  "security",
  "review",
  "pr",
];
