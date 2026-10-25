import type { RetainedJournalEntry } from "./clientJournalStorage";
import { ApiError, plotloomApi } from "../../api";
import type { AuthoringDraft } from "../../types";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";
import { sameDraftPayload } from "../../app/workspace/contracts";

export type ReviewEditor = "source" | "cast" | "art" | "script" | "production_intent" | "production_presentation" | "shot_presentation" | "character_reference" | "art_reference" | "same_person" | "cast_settings" | "art_settings" | "managed_reference" | "keyframe_compatibility" | "material_review" | "text_retry" | "video_directions" | "take_rejection" | "h3_directions" | "video_pack_notes" | "video_segment_notes" | "brief_custom";
export type ReviewBuffer = { editor: ReviewEditor; targetId?: string; basis: string; text: string };
type Entry = { payload: ReviewBuffer; baseRevision: number; localRevision: number; editing: boolean; expectedDraftRevision: number; conflict?: boolean; failed?: boolean; ownershipConflict?: boolean };
type Storage = Pick<globalThis.Storage, "getItem" | "setItem"> & { discardCurrentEntry?: (key: string, entryKey: string, selected: unknown) => void; retainedEntries?: (key: string) => RetainedJournalEntry[]; discardRetained?: (entry: RetainedJournalEntry) => void };
const storageKey = "plotloom:review-editor-drafts:v1";
const entityFor = (editor: ReviewEditor, target = "") => target ? `${editor}:${target}` : editor;

/** Typed working input only. Adoption, consent and dispatch never live here. */
export function createReviewDraftStore(quiescence: ProjectDraftQuiescence, storage: Storage) {
  const entries = new Map<string, Entry>();
  const remote = new Map<string, AuthoringDraft>();
  const rejectedInputs = new Map<string, ReviewBuffer>();
  const flights = new Map<string, Promise<boolean>>();
  const timers = new Map<string, ReturnType<typeof setTimeout>>();
  const abandoning = new Set<string>(), suspended = new Set<string>();
  const listeners = new Set<() => void>();
  let version = 0, storageFailed = false;
  const keyFor = (projectId: string, editor: ReviewEditor, target = "") => `${projectId}:${entityFor(editor, target)}`;
  try {
    const saved = JSON.parse(storage.getItem(storageKey) || "{}");
    for (const [key, item] of Object.entries(saved)) {
      const entry = item as Entry;
      if (entry?.payload && typeof entry.payload.text === "string" && typeof entry.payload.basis === "string" && Number.isInteger(entry.baseRevision)) entries.set(key, { ...entry, editing: true, conflict: entry.conflict || entry.ownershipConflict });
    }
  } catch { storageFailed = true; }
  const notify = () => { quiescence.changed(); version += 1; listeners.forEach(listener => listener()); };
  const persistLocal = () => {
    try {
      const serialized = JSON.stringify(Object.fromEntries(entries));
      storage.setItem(storageKey, serialized);
      if (storage.getItem(storageKey) !== serialized) throw new Error("journal readback failed");
      storageFailed = false;
    } catch { storageFailed = true; }
    notify();
  };
  const schedule = (projectId: string, editor: ReviewEditor, target = "") => {
    const key = keyFor(projectId, editor, target);
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(() => { timers.delete(key); void flush(projectId, editor, target); }, 600));
  };
  const retainedFor = (projectId: string, editor: ReviewEditor, target = "") => (storage.retainedEntries?.(storageKey) ?? [])
    .filter(item => item.key === keyFor(projectId, editor, target));
  const retireExactRetained = (projectId: string, editor: ReviewEditor, target: string, draft: AuthoringDraft) => {
    for (const selected of retainedFor(projectId, editor, target)) {
      const entry = selected.value as Entry;
      if (entry.baseRevision === draft.baseCanonicalRevision && (entry.expectedDraftRevision === draft.draftRevision || entry.expectedDraftRevision + 1 === draft.draftRevision) && sameDraftPayload(entry.payload, draft.payload)) {
        try { storage.discardRetained?.(selected); } catch { /* A newer revision stays visible. */ }
      }
    }
  };
  const register = (projectId: string, editor: ReviewEditor, target = "") => {
    quiescence.register(projectId, `review_buffer:${entityFor(editor, target)}`, () => flush(projectId, editor, target), {
      retainOnUnmount: true,
      locallyPreserved: () => !storageFailed && !rejectedInputs.has(keyFor(projectId, editor, target)),
      pending: () => {
        const entry = entries.get(keyFor(projectId, editor, target));
        return rejectedInputs.has(keyFor(projectId, editor, target)) || Boolean(entry && !sameDraftPayload(remote.get(keyFor(projectId, editor, target))?.payload, entry.payload));
      },
      suspendWrites: async () => {
        const key = keyFor(projectId, editor, target); suspended.add(key); clearTimeout(timers.get(key)); await flights.get(key);
        return () => { suspended.delete(key); schedule(projectId, editor, target); };
      },
      discardUnsent: async () => {
        const key = keyFor(projectId, editor, target); abandoning.add(key); clearTimeout(timers.get(key)); await flights.get(key); entries.delete(key); rejectedInputs.delete(key); persistLocal();
      },
    });
  };
  const flush = async (projectId: string, editor: ReviewEditor, target = ""): Promise<boolean> => {
    const key = keyFor(projectId, editor, target); clearTimeout(timers.get(key)); timers.delete(key);
    if (rejectedInputs.has(key)) return false;
    while (entries.has(key)) {
      const entry = entries.get(key)!;
      const receipt = remote.get(key);
      if (receipt?.baseCanonicalRevision === entry.baseRevision && sameDraftPayload(receipt.payload, entry.payload)) return true;
      if (entry.conflict || abandoning.has(key) || suspended.has(key) || !quiescence.canWrite(projectId)) return false;
      const flight = flights.get(key);
      if (flight) { if (!await flight) return false; continue; }
      const accept = (saved: AuthoringDraft) => {
        remote.set(key, saved);
        const current = entries.get(key);
        if (current) { current.expectedDraftRevision = saved.draftRevision; current.failed = false; }
        persistLocal(); retireExactRetained(projectId, editor, target, saved); return true;
      };
      const request = plotloomApi.saveAuthoringDraft(projectId, {
        editorScope: "review_buffer", entityId: entityFor(editor, target), baseCanonicalRevision: entry.baseRevision,
        expectedDraftRevision: entry.expectedDraftRevision, payload: entry.payload,
      }).then(accept).catch(async error => {
        // A failed response is not permission to replay. Recover only the exact
        // one-step receipt; different revisions/content remain competing work.
        try {
          const observed = (await plotloomApi.getAuthoringDrafts(projectId)).find(draft => draft.editorScope === "review_buffer" && draft.entityId === entityFor(editor, target));
          if (observed && observed.baseCanonicalRevision === entry.baseRevision && observed.draftRevision === entry.expectedDraftRevision + 1 && sameDraftPayload(observed.payload, entry.payload)) return accept(observed);
        } catch { /* The verified local journal remains the preservation path. */ }
        const current = entries.get(key);
        if (current) { current.failed = true; current.conflict = error instanceof ApiError && error.status === 409; }
        persistLocal(); return false;
      });
      flights.set(key, request);
      const success = await request; flights.delete(key);
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
      for (const key of entries.keys()) if (key.startsWith(`${projectId}:`)) { clearTimeout(timers.get(key)); entries.delete(key); }
      for (const key of remote.keys()) if (key.startsWith(`${projectId}:`)) remote.delete(key);
      for (const key of rejectedInputs.keys()) if (key.startsWith(`${projectId}:`)) rejectedInputs.delete(key);
      persistLocal(); if (storageFailed) throw new Error("项目已删除，但本地审阅草稿缓存未能清除");
    },
    hydrate(projectId: string, drafts: AuthoringDraft[]) {
      if (quiescence.isClosing(projectId)) return;
      for (const key of abandoning) if (key.startsWith(`${projectId}:`)) abandoning.delete(key);
      for (const draft of drafts) {
        if (draft.projectId !== projectId || draft.editorScope !== "review_buffer") continue;
        const payload = draft.payload as ReviewBuffer;
        if (entityFor(payload.editor, payload.targetId) !== draft.entityId) continue;
        const key = keyFor(projectId, payload.editor, payload.targetId); remote.set(key, draft);
        retireExactRetained(projectId, payload.editor, payload.targetId ?? "", draft);
        const local = entries.get(key);
        if (!local) entries.set(key, { payload, baseRevision: draft.baseCanonicalRevision, localRevision: 0, editing: true, expectedDraftRevision: draft.draftRevision });
        else if (local.baseRevision === draft.baseCanonicalRevision && (local.expectedDraftRevision === draft.draftRevision || local.expectedDraftRevision + 1 === draft.draftRevision) && sameDraftPayload(local.payload, payload)) {
          local.expectedDraftRevision = draft.draftRevision; local.conflict = false; local.failed = false; local.ownershipConflict = false;
        } else if (local.expectedDraftRevision !== draft.draftRevision) local.conflict = true;
      }
      for (const [key, entry] of entries) if (key.startsWith(`${projectId}:`)) {
        register(projectId, entry.payload.editor, entry.payload.targetId); if (!entry.conflict) schedule(projectId, entry.payload.editor, entry.payload.targetId);
      }
      notify();
    },
    get(projectId: string, editor: ReviewEditor, target = "") { return entries.get(keyFor(projectId, editor, target)); },
    rejected(projectId: string, editor: ReviewEditor, target = "") { return rejectedInputs.get(keyFor(projectId, editor, target)); },
    retained: retainedFor,
    discardRetained(selected: RetainedJournalEntry) { storage.discardRetained?.(selected); notify(); },
    resumeRetained(projectId: string, editor: ReviewEditor, target: string, basis: string, baseRevision: number, selected: RetainedJournalEntry) {
      if (!quiescence.canWrite(projectId) || quiescence.isClosing(projectId)) throw new Error("当前项目不允许恢复编辑输入。");
      const source = retainedFor(projectId, editor, target).find(item => item.namespace === selected.namespace && item.key === selected.key && item.serialized === selected.serialized);
      if (!source) throw new Error("保留输入已变化；请重新核对。");
      const entry = source.value as Entry, key = keyFor(projectId, editor, target), current = entries.get(key);
      if (current && !sameDraftPayload(current.payload, remote.get(key)?.payload)) throw new Error("请先保留或明确丢弃当前会话的输入。");
      if (entry.payload.basis !== basis || entry.baseRevision !== baseRevision || entry.expectedDraftRevision !== (remote.get(key)?.draftRevision ?? 0)) throw new Error("来源或服务器草稿已变化；可复制这份输入，不能直接恢复。");
      entries.set(key, { ...entry, editing: true, conflict: false, ownershipConflict: false, localRevision: entry.localRevision + 1 });
      register(projectId, editor, target); persistLocal();
      if (storageFailed) throw new Error("本会话输入尚未在本机保留；原会话输入保持不变。");
      storage.discardRetained?.(selected); schedule(projectId, editor, target); notify();
    },
    leave(_projectId: string) { /* Retained writers and journals survive navigation. */ },
    update(projectId: string, editor: ReviewEditor, baseRevision: number, basis: string, text: string, target = "") {
      if (quiescence.isClosing(projectId) || !quiescence.canWrite(projectId)) return false;
      const key = keyFor(projectId, editor, target), previous = entries.get(key);
      if (previous && (previous.payload.basis !== basis || previous.baseRevision !== baseRevision)) {
        rejectedInputs.set(key, { editor, targetId: target, basis, text });
        previous.conflict = true; register(projectId, editor, target); persistLocal(); return false;
      }
      if (previous?.payload.text === text && previous.payload.basis === basis) return true;
      const payload: ReviewBuffer = { editor, targetId: target, basis: previous?.payload.basis ?? basis, text };
      entries.set(key, { payload, baseRevision: previous?.baseRevision ?? baseRevision, localRevision: (previous?.localRevision ?? 0) + 1,
        editing: true, expectedDraftRevision: previous?.expectedDraftRevision ?? remote.get(key)?.draftRevision ?? 0, conflict: previous?.conflict });
      rejectedInputs.delete(key); register(projectId, editor, target); persistLocal(); schedule(projectId, editor, target); return true;
    },
    restore(projectId: string, editor: ReviewEditor, target = "") { const entry = entries.get(keyFor(projectId, editor, target)); if (entry) { entry.editing = true; persistLocal(); } },
    async clear(projectId: string, editor: ReviewEditor, target = "", selected?: Entry | null) {
      const key = keyFor(projectId, editor, target), entry = selected === undefined ? entries.get(key) : selected ?? undefined;
      if (entries.get(key) !== entry) return;
      if (rejectedInputs.has(key)) throw new Error("当前来源变化后的输入尚未保留，请先复制或明确丢弃。");
      clearTimeout(timers.get(key)); await flights.get(key);
      if (entries.get(key) !== entry) return;
      if (!quiescence.canWrite(projectId)) throw new Error("当前项目不允许修改审阅草稿");
      const receipt = remote.get(key);
      if (receipt && entry && entry.expectedDraftRevision === receipt.draftRevision && sameDraftPayload(entry.payload, receipt.payload)) {
        const consumed = await plotloomApi.discardAuthoringDraft(projectId, { editorScope: "review_buffer", entityId: entityFor(editor, target), expectedDraftRevision: receipt.draftRevision });
        if (consumed !== receipt.draftRevision) throw new Error("草稿回执已变化");
        if (remote.get(key) === receipt) remote.delete(key);
      } else if (receipt && entry?.conflict) throw new Error("review draft changed in another client");
      if (entries.get(key) === entry) { storage.discardCurrentEntry?.(storageKey, key, entry); entries.delete(key); } persistLocal();
    },
    flush,
  };
}
export type ReviewDraftStore = ReturnType<typeof createReviewDraftStore>;
