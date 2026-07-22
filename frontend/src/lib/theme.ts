import { safeStorage } from "./storage";

export type ThemePreference = "dark" | "light" | "system";

const STORAGE_KEY = "agentsystem-theme";
export const THEME_CHANGE_EVENT = "agentsystem:theme-change";

export function getThemePreference(): ThemePreference {
  const value = safeStorage.get(STORAGE_KEY);
  return value === "dark" || value === "light" || value === "system" ? value : "system";
}

export function applyTheme(preference: ThemePreference): void {
  const dark = preference === "dark" || (preference === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

export function setThemePreference(preference: ThemePreference): void {
  safeStorage.set(STORAGE_KEY, preference);
  applyTheme(preference);
  window.dispatchEvent(new CustomEvent<ThemePreference>(THEME_CHANGE_EVENT, { detail: preference }));
}
