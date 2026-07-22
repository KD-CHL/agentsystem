import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import "../i18n";
import { CommandPalette } from "../components/CommandPalette";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    session: { user: { display_name: "Tester", username: "tester", role: "admin" }, auth_mode: "dev" },
    can: () => true,
    logout: vi.fn(),
  }),
}));

vi.mock("../lib/api", () => ({
  api: {
    tasks: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    projects: vi.fn().mockResolvedValue([]),
    agents: vi.fn().mockResolvedValue([]),
  },
}));

function renderPalette(open: boolean) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CommandPalette open={open} onClose={() => undefined} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    renderPalette(false);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("lists page navigation when open with an empty query", () => {
    renderPalette(true);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("页面")).toBeInTheDocument();
    expect(screen.getByText("工作台")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("filters pages as the user types", async () => {
    const user = userEvent.setup();
    renderPalette(true);
    const input = screen.getByRole("combobox");
    await user.type(input, "settings");
    // After the debounce the pages group narrows to the matching entry.
    await waitFor(() => {
      expect(screen.getByText("设置")).toBeInTheDocument();
      expect(screen.queryByText("工作台")).toBeNull();
    });
  });
});
