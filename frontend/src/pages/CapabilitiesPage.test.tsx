import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../i18n";
import type { AgentName, McpServer } from "../types";

const apiMock = vi.hoisted(() => ({
  mcpServers: vi.fn(),
  skills: vi.fn(),
  capabilityPolicy: vi.fn(),
  credentials: vi.fn(),
  agentCapabilities: vi.fn(),
  createMcpServer: vi.fn(),
  updateMcpServer: vi.fn(),
  deleteMcpServer: vi.fn(),
  validateMcpServer: vi.fn(),
  pickSkill: vi.fn(),
  refreshSkill: vi.fn(),
  updateSkill: vi.fn(),
  deleteSkill: vi.fn(),
  updateAgentCapabilities: vi.fn(),
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

import { CapabilitiesPage } from "./CapabilitiesPage";

const server: McpServer = {
  id: "mcp_local",
  tenant_id: "default",
  name: "Local tools",
  description: "Local repository tools",
  transport: "streamable_http",
  url: "http://127.0.0.1:3001/mcp",
  command: null,
  args: [],
  credential_ref: null,
  credential_header: "Authorization",
  credential_scheme: "Bearer",
  credential_env: null,
  tool_allowlist: [],
  approval_policy: "always",
  enabled: false,
  timeout_seconds: 15,
  status: "untested",
  tools: [],
  last_error: null,
  last_validated_at: null,
  version: 1,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};

describe("CapabilitiesPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("en");
    apiMock.mcpServers.mockResolvedValue([]);
    apiMock.skills.mockResolvedValue([]);
    apiMock.credentials.mockResolvedValue([]);
    apiMock.capabilityPolicy.mockResolvedValue({
      network_enabled: true,
      allowed_hosts: ["127.0.0.1", "localhost"],
      stdio_enabled: false,
      stdio_allowed_commands: ["npx"],
      skill_allowed_roots: ["/Users/test"],
      skill_max_bytes: 65_536,
    });
    apiMock.agentCapabilities.mockImplementation(async (name: AgentName) => ({
      agent_name: name,
      mcp_servers: [],
      skills: [],
    }));
    apiMock.createMcpServer.mockResolvedValue(server);
  });

  it("creates an MCP server from the registry workflow", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(<QueryClientProvider client={client}><CapabilitiesPage /></QueryClientProvider>);

    await user.click(await screen.findByRole("button", { name: "Add server" }));
    await user.type(screen.getByRole("textbox", { name: "Name" }), "Local tools");
    await user.click(screen.getByRole("button", { name: "Create server" }));

    await waitFor(() => expect(apiMock.createMcpServer).toHaveBeenCalledWith(expect.objectContaining({
      name: "Local tools",
      transport: "streamable_http",
      url: "http://127.0.0.1:3001/mcp",
      enabled: false,
    })));
  });
});
