import { beforeEach, describe, expect, it, vi } from "vitest";

import { applyTheme, getThemePreference, setThemePreference, THEME_CHANGE_EVENT } from "./theme";

describe("theme preferences", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("defaults to system and applies the resolved color mode", () => {
    expect(getThemePreference()).toBe("system");
    applyTheme("system");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("persists explicit dark mode", () => {
    const listener = vi.fn();
    window.addEventListener(THEME_CHANGE_EVENT, listener);
    setThemePreference("dark");
    expect(getThemePreference()).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(THEME_CHANGE_EVENT, listener);
  });
});
