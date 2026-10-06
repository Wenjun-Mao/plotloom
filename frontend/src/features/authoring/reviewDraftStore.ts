import { plotloomApi } from "../../api";
import type { AuthoringDraft } from "../../types";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";

export type ReviewEditor = "source" | "cast" | "art" | "script";
export type ReviewBuffer = { editor: ReviewEditor; basis: string; text: string };
type Entry = { payload: ReviewBuffer; baseRevision: number; localRevision: number; editing: boolean; expectedDraftRevision: number };
type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;
const storageKey = "plotloom:review-editor-drafts:v1";

/** Narrow tab safety plus exact server CAS; no accepted review writes live here. */
export function createReviewDraftStore(quiescence: ProjectDraftQuiescence, storage: Storage) {
  const entries = new Map<string, Entry>();
  const remote = new Map<string, AuthoringDraft>();
  const flights = new Map<string, Promise<boolean>>();
  const abandoning = new Set<string>();
  const suspended = new Set<string>();
  const listeners = new Set<() => void>();
  let version = 0;
  let storageFailed = false;
  const keyFor = (projectId: string, editor: ReviewEditor) => `${projectId}:${editor}`;
  try {
    const saved = JSON.parse(storage.getItem(storageKey) || "{}");
    for (const [key, item] of Object.entries(saved)) {
      const entry = item as Entry;
      if (entry?.payload && ["source", "cast", "art", "script"].includes(entry.payload.editor)
        && typeof entry.payload.text === "string" && typeof entry.payload.basis === "string" && Number.isInteger(entry.baseRevision)) {
        entries.set(key, { ...entry, editing: false });
      }
    }
  } catch { storageFailed = true; }
  const notify = () => { version += 1; listeners.forEach(listener => listener()); };
  const persistLocal = () => {
    try { storage.setItem(storageKey, JSON.stringify(Object.fromEntries(entries))); storageFailed = false; }
    catch { storageFailed = true; }
    notify();
  };
  const register = (projectId: string, editor: ReviewEditor) => {
    quiescence.register(projectId, `review_buffer:${editor}`, () => flush(projectId, editor), {
      retainOnUnmount: true,
      suspendWrites: async () => {
        const key = keyFor(projectId, editor);
        suspended.add(key);
        await flights.get(key);
        return () => { suspended.delete(key); };
      },
      discardUnsent: async () => {
        const key = keyFor(projectId, editor);
        abandoning.add(key);
        await flights.get(key);
        entries.delete(key);
        persistLocal();
      },
    });
  };
  const flush = async (projectId: string, editor: ReviewEditor): Promise<boolean> => {
    const key = keyFor(projectId, editor);
    while (entries.has(key)) {
      if (abandoning.has(key) || suspended.has(key)) return false;
      const flight = flights.get(key);
      if (flight) { if (!await flight) return false; continue; }
      const entry = entries.get(key)!;
      const receipt = remote.get(key);
      if (receipt?.baseCanonicalRevision === entry.baseRevision && JSON.stringify(receipt.payload) === JSON.stringify(entry.payload)) return true;
      const request = plotloomApi.saveAuthoringDraft(projectId, {
        editorScope: "review_buffer", entityId: editor, baseCanonicalRevision: entry.baseRevision,
        expectedDraftRevision: entry.expectedDraftRevision, payload: entry.payload,
      }).then(saved => {
        remote.set(key, saved);
        const current = entries.get(key);
        if (current) current.expectedDraftRevision = saved.draftRevision;
        persistLocal(); return true;
      }).catch(() => false);
      flights.set(key, request);
      const success = await request;
      flights.delete(key);
      if (!success) return false;
      if (entries.get(key) === entry) return true;
    }
    return true;
  };
  return {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    snapshot: () => version,
    storageFailed: () => storageFailed,
    eraseProject(projectId: string) {
      for (const key of entries.keys()) if (key.startsWith(`${projectId}:`)) entries.delete(key);
      for (const key of remote.keys()) if (key.startsWith(`${projectId}:`)) remote.delete(key);
      persistLocal();
      if (storageFailed) throw new Error("项目已删除，但本地审阅草稿缓存未能清除");
    },
    hydrate(projectId: string, drafts: AuthoringDraft[]) {
      if (quiescence.isClosing(projectId)) return;
      for (const key of abandoning) if (key.startsWith(`${projectId}:`)) abandoning.delete(key);
      for (const draft of drafts) {
        if (draft.projectId !== projectId || draft.editorScope !== "review_buffer") continue;
        const payload = draft.payload as ReviewBuffer;
        if (payload.editor !== draft.entityId) continue;
        const key = keyFor(projectId, payload.editor);
        remote.set(key, draft);
        if (!entries.has(key)) entries.set(key, { payload, baseRevision: draft.baseCanonicalRevision, localRevision: 0, editing: false, expectedDraftRevision: draft.draftRevision });
        register(projectId, payload.editor);
      }
      // A local unsent buffer must stay visible to Close after a route remount.
      for (const [key, entry] of entries) if (key.startsWith(`${projectId}:`)) register(projectId, entry.payload.editor);
      notify();
    },
    get(projectId: string, editor: ReviewEditor) { return entries.get(keyFor(projectId, editor)); },
    leave(projectId: string) {
      for (const [key, entry] of entries) if (key.startsWith(`${projectId}:`)) entry.editing = false;
      persistLocal();
    },
    update(projectId: string, editor: ReviewEditor, baseRevision: number, basis: string, text: string) {
      if (quiescence.isClosing(projectId)) return;
      const key = keyFor(projectId, editor);
      const previous = entries.get(key);
      entries.set(key, { payload: { editor, basis: previous?.payload.basis ?? basis, text },
        baseRevision: previous?.baseRevision ?? baseRevision, localRevision: (previous?.localRevision ?? 0) + 1, editing: true,
        expectedDraftRevision: previous?.expectedDraftRevision ?? remote.get(key)?.draftRevision ?? 0 });
      register(projectId, editor); persistLocal();
    },
    restore(projectId: string, editor: ReviewEditor) {
      const entry = entries.get(keyFor(projectId, editor));
      if (entry && !quiescence.isClosing(projectId)) { entry.editing = true; persistLocal(); }
    },
    async clear(projectId: string, editor: ReviewEditor) {
      const key = keyFor(projectId, editor);
      const entry = entries.get(key);
      await flights.get(key);
      const receipt = remote.get(key);
      if (receipt && (!entry || entry.expectedDraftRevision === receipt.draftRevision)) {
        await plotloomApi.discardAuthoringDraft(projectId, { editorScope: "review_buffer", entityId: editor, expectedDraftRevision: receipt.draftRevision });
        if (remote.get(key) === receipt) remote.delete(key);
      } else if (receipt) {
        throw new Error("review draft changed in another client");
      }
      if (entries.get(key) === entry) entries.delete(key);
      persistLocal();
    },
    flush,
  };
}
export type ReviewDraftStore = ReturnType<typeof createReviewDraftStore>;
