const STORAGE_KEY = "plotloom:provider-session-keys";
const LEGACY_STORAGE_KEY = "plotloom:provider-session-key";

type SessionKeyMap = Record<string, string>;

function readMap(): SessionKeyMap {
  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    if (!stored) {
      const legacy = window.sessionStorage.getItem(LEGACY_STORAGE_KEY)?.trim();
      return legacy ? { default: legacy } : {};
    }
    const parsed: unknown = JSON.parse(stored);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).flatMap(([profileId, value]) =>
      typeof value === "string" && value.trim() ? [[profileId, value.trim()]] : [],
    ));
  } catch {
    return {};
  }
}

function writeMap(keys: SessionKeyMap): void {
  try {
    if (Object.keys(keys).length) window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
    else window.sessionStorage.removeItem(STORAGE_KEY);
    // The former single-key entry is intentionally migrated out of the current
    // session rather than copied to durable storage.
    window.sessionStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // A disabled storage implementation must not block the workbench.
  }
}

export const providerSessionKeys = {
  read(profileId: string): string {
    return readMap()[profileId] || "";
  },
  write(profileId: string, value: string): void {
    const keys = readMap();
    const key = value.trim();
    if (key) keys[profileId] = key;
    else delete keys[profileId];
    writeMap(keys);
  },
  clear(profileId: string): void {
    this.write(profileId, "");
  },
};

/** @deprecated Use the profile-scoped providerSessionKeys API. */
export const providerSessionKey = {
  read(): string {
    return providerSessionKeys.read("default");
  },
  write(value: string): void {
    providerSessionKeys.write("default", value);
  },
  clear(): void {
    providerSessionKeys.clear("default");
  },
};
