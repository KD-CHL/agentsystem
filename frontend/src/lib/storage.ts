function storage(): Storage | null {
  try {
    return typeof window !== "undefined" && window.localStorage ? window.localStorage : null;
  } catch {
    return null;
  }
}

export const safeStorage = {
  get(key: string): string | null {
    try {
      return storage()?.getItem(key) ?? null;
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      storage()?.setItem(key, value);
    } catch {
      // Preferences remain in memory when browser storage is unavailable.
    }
  },
};
