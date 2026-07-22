import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "../i18n";
import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("creates a same-origin session and returns the authenticated user", async () => {
    const session = {
      auth_mode: "local",
      user: {
        id: "user_1", tenant_id: "default", username: "admin", display_name: "Administrator",
        role: "admin", status: "active", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), last_login_at: null,
      },
    } as const;
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(session), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const signedIn = vi.fn();
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><LoginPage onSignedIn={signedIn} /></QueryClientProvider>);

    fireEvent.change(screen.getByRole("textbox", { name: /username|用户名/i }), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/password|密码/i), { target: { value: "test-only-admin-password" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in|登录工作台/i }));

    await waitFor(() => expect(signedIn).toHaveBeenCalledWith(session));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({ method: "POST", credentials: "include" }));
  });
});
