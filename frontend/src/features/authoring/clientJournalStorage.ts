/** Per-document writes fence cloned session IDs; retained rows keep exact identity. */
const documentIdentity = crypto.randomUUID();
let client: string | undefined;
export function draftClientIdentity(): string {
  if (!client) {
    try {
      client = sessionStorage.getItem("plotloom:draft-client") || crypto.randomUUID();
      sessionStorage.setItem("plotloom:draft-client", client);
    } catch { client = crypto.randomUUID(); }
  }
  return `${client}:${documentIdentity}`;
}
export type RetainedJournalEntry = { namespace: string; key: string; serialized: string; value: Record<string, unknown> };
export const clientJournalStorage = {
  getItem(key: string) { return localStorage.getItem(`${key}:client:${draftClientIdentity()}`) ?? sessionStorage.getItem(key); },
  setItem(key: string, value: string) {
    const owned = `${key}:client:${draftClientIdentity()}`;
    localStorage.setItem(owned, value);
    if (localStorage.getItem(owned) !== value) throw new Error("作者输入的本地回读未确认");

  },
  namespace(key: string) { return `${key}:client:${draftClientIdentity()}`; },
  retainedEntries(key: string): RetainedJournalEntry[] {
    const own = `${key}:client:${draftClientIdentity()}`;
    const retained: RetainedJournalEntry[] = [];
    for (let index = 0; index < localStorage.length; index++) {
      const namespace = localStorage.key(index);
      if (!namespace?.startsWith(`${key}:client:`) || namespace === own) continue;
      const records: unknown = JSON.parse(localStorage.getItem(namespace) || "{}");
      if (!records || typeof records !== "object" || Array.isArray(records)) throw new Error("保留输入的命名空间格式无法确认");
      for (const [entryKey, value] of Object.entries(records)) if (value && typeof value === "object" && !Array.isArray(value)) retained.push({ namespace, key: entryKey, serialized: JSON.stringify(value), value });
    }
    // Current data never hides a distinct legacy tab journal.
    const legacy = sessionStorage.getItem(key);
    if (legacy && localStorage.getItem(own) !== null) {
      for (const [entryKey, value] of Object.entries(JSON.parse(legacy))) if (value && typeof value === "object" && !Array.isArray(value)) retained.push({ namespace: `session:${key}`, key: entryKey, serialized: JSON.stringify(value), value: value as Record<string, unknown> });
    }
    return retained;
  },
  discardCurrentEntry(key: string, entryKey: string, selected: unknown) {
    const legacy = sessionStorage.getItem(key);
    if (!legacy) return;
    const entries = JSON.parse(legacy), retained = entries[entryKey];
    const entry = selected as Record<string, unknown>;
    const same = retained && ("payload" in entry
      ? JSON.stringify(retained.payload) === JSON.stringify(entry.payload) && retained.localRevision === entry.localRevision && retained.baseRevision === entry.baseRevision
      : JSON.stringify(retained.value) === JSON.stringify(entry.value) && retained.baseId === entry.baseId && retained.contextId === entry.contextId);
    if (same) {
      delete entries[entryKey]; sessionStorage.setItem(key, JSON.stringify(entries));
    }
  },
  discardRetained(selected: RetainedJournalEntry) {
    const storage = selected.namespace.startsWith("session:") ? sessionStorage : localStorage;
    const namespace = selected.namespace.startsWith("session:") ? selected.namespace.slice(8) : selected.namespace;
    const records = JSON.parse(storage.getItem(namespace) || "{}");
    if (!(selected.key in records)) return;
    if (JSON.stringify(records[selected.key]) !== selected.serialized) throw new Error("保留输入已变化；请查看最新版本后重试。");
    delete records[selected.key];
    storage.setItem(namespace, JSON.stringify(records));
  },
};
