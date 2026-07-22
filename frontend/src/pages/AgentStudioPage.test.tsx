import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../i18n";
import type { AgentConfiguration } from "../types";

const apiMock = vi.hoisted(() => ({
  agents: vi.fn(),
  modelProviders: vi.fn(),
  credentials: vi.fn(),
  updateAgent: vi.fn(),
  validateAgent: vi.fn(),
  discoverAgentModels: vi.fn(),
  createCredential: vi.fn(),
  deleteCredential: vi.fn(),
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

import { AgentStudioPage } from "./AgentStudioPage";

const simulatedConfiguration: AgentConfiguration = {
  agent_name: "orchestrator",
  provider_id: "simulated",
  model: "deterministic-local",
  credential_ref: null,
  api_key_env: null,
  credential_available: false,
  base_url: null,
  api_format: "responses",
  call_mode: "simulated",
  timeout_seconds: 60,
  max_output_tokens: 4096,
  budget_limit: null,
  version: 1,
  network_enabled: false,
};

describe("AgentStudioPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("en");
    apiMock.agents.mockResolvedValue([{
      agent_name: "orchestrator",
      display_name: "Orchestrator",
      description: "Coordinates the workflow",
      status: "idle",
      last_summary: null,
      handoff_to: null,
      latency_ms: null,
      configuration: simulatedConfiguration,
    }]);
    apiMock.modelProviders.mockResolvedValue([
      {
        id: "simulated",
        display_name: "Simulated",
        description: "No network",
        default_api_format: "responses",
        supported_api_formats: ["responses"],
        default_base_url: null,
        requires_base_url: false,
        requires_credential: false,
        default_model: "deterministic-local",
        models: ["deterministic-local"],
        supports_model_discovery: false,
      },
      {
        id: "openai",
        display_name: "OpenAI",
        description: "Official OpenAI Responses API.",
        default_api_format: "responses",
        supported_api_formats: ["responses", "chat_completions"],
        default_base_url: "https://api.openai.com/v1",
        requires_base_url: false,
        requires_credential: true,
        default_model: "gpt-5.6-terra",
        models: ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
        supports_model_discovery: true,
      },
    ]);
    apiMock.credentials.mockResolvedValue([]);
    apiMock.updateAgent.mockImplementation(async (_name: string, payload: Record<string, unknown>) => ({
      ...simulatedConfiguration,
      ...payload,
      version: 2,
      network_enabled: payload.call_mode === "live",
    }));
  });

  it("applies a provider preset and saves a live per-agent profile", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(<QueryClientProvider client={client}><AgentStudioPage /></QueryClientProvider>);

    await screen.findByRole("button", { name: /Orchestrator/ });
    await user.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "openai");

    expect(screen.getByRole("combobox", { name: "Model" })).toHaveValue("gpt-5.6-terra");
    expect(screen.getByRole("textbox", { name: "Base URL" })).toHaveValue("https://api.openai.com/v1");
    expect(screen.getByRole("combobox", { name: "API format" })).toHaveValue("responses");
    expect(screen.getByRole("combobox", { name: "Call mode" })).toHaveValue("live");

    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(apiMock.updateAgent).toHaveBeenCalledWith("orchestrator", expect.objectContaining({
      provider_id: "openai",
      model: "gpt-5.6-terra",
      api_format: "responses",
      call_mode: "live",
    })));
  });
});
