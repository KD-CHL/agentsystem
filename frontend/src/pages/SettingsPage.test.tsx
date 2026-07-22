import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../i18n";
import { SettingsPage } from "./SettingsPage";

const logout = vi.fn().mockResolvedValue(undefined);

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    session: {
      auth_mode: "dev",
      user: {
        id: "user_local_admin",
        tenant_id: "default",
        display_name: "Local Administrator",
        username: "local-admin",
        role: "admin",
        status: "active",
      },
    },
    can: () => true,
    logout,
  }),
}));

vi.mock("../lib/api", () => ({
  api: {
    system: vi.fn().mockResolvedValue({
      name: "AgentSystem",
      version: "0.3.0",
      auth_mode: "dev",
      execution_mode: "mixed",
      model_calls_enabled: true,
      live_agent_count: 3,
      simulated_agent_count: 5,
      worker_running: true,
    }),
  },
}));

describe("SettingsPage", () => {
  beforeEach(async () => {
    localStorage.clear();
    logout.mockClear();
    await i18n.changeLanguage("zh");
  });

  afterEach(() => cleanup());

  it("switches language and keeps runtime safety visible", async () => {
    renderSettings();

    fireEvent.click(screen.getByRole("radio", { name: /English/i }));

    expect(screen.getByText("System settings")).toBeInTheDocument();
    expect(screen.getByText("Per-agent configured execution")).toBeInTheDocument();
    expect(await screen.findByText("Workflow worker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Agent Studio/i })).toHaveAttribute("href", "/agents");
  });

  it("applies a theme immediately and reports browser persistence", () => {
    renderSettings();

    fireEvent.click(screen.getByRole("radio", { name: /深色/ }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(screen.getByText("已保存到此浏览器")).toBeInTheDocument();
  });
});

function renderSettings() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
