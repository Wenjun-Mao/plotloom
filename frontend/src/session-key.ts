const STORAGE_KEY = "plotloom:provider-session-key";

export const providerSessionKey = {
  read(): string {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) || "";
    } catch {
      return "";
    }
  },
  write(value: string): void {
    const key = value.trim();
    try {
      if (key) window.sessionStorage.setItem(STORAGE_KEY, key);
      else window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // A disabled storage implementation must not block the workbench.
    }
  },
  clear(): void {
    this.write("");
  },
};
