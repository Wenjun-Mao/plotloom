import { useRetainedMediaJournal } from "./features/authoring/useRetainedMediaJournal";
import { saveWorkingDraft } from "./features/authoring/saveWorkingDraft";
import { clientJournalStorage } from "./features/authoring/clientJournalStorage";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, plotloomApi } from "./api";
import type { ProjectDraftQuiescence } from "./features/authoring/projectDraftQuiescence";
import { discardMediaDraftEntry, useMediaDraftErasure } from "./features/authoring/projectDraftCache";

export type IntentDraft = { identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string; sourceBindingId?: string; retainedVisualIntentId?: string };
type Entry = { baseId: string | null; value: IntentDraft; expectedDraftRevision?: number; ownershipConflict?: boolean };
type Drafts = Record<string, Entry>;
type DurableWriterState = {
  serverRevision: number;
  acknowledgedPayload?: string;
  persistence?: Promise<void>;
  timer?: number;
  serverReady: boolean;
  serverConflict: boolean;
  requestEpoch: number;
  abandoning?: boolean;
  suspended?: boolean;
};
const storageKey = "plotloom:visual-intent-drafts:v1";
const fields = ["identityIntent", "compositionIntent", "styleIntent", "sourceRefs", "sourceBindingId", "retainedVisualIntentId"] as const;

function durableWriterStateFor(
  states: Map<string, DurableWriterState>,
  entityId: string,
): DurableWriterState {
  let state = states.get(entityId);
  if (!state) {
    state = { serverRevision: 0, serverReady: false, serverConflict: false, requestEpoch: 0 };
    states.set(entityId, state);
  }
  return state;
}

function readSessionDrafts<EntryValue>(
  key: string,
  isEntry: (value: unknown) => value is EntryValue,
): Record<string, EntryValue> {
  try {
    const value: unknown = JSON.parse(clientJournalStorage.getItem(key) ?? "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const entries = Object.entries(value);
    return Object.fromEntries(
      entries.filter((entry): entry is [string, EntryValue] => isEntry(entry[1])),
    );
  } catch { return {}; }
}

function isIntentDraftEntry(value: unknown): value is Entry {
  if (!value || typeof value !== "object") return false;
  const entry = value as Partial<Entry>;
  return (entry.baseId === null || typeof entry.baseId === "string")
    && Boolean(entry.value)
    && fields.every((field) => typeof entry.value?.[field] === "string" || ((field === "sourceBindingId" || field === "retainedVisualIntentId") && entry.value?.[field] === undefined));
}

function readDrafts(): Drafts {
  return readSessionDrafts(storageKey, isIntentDraftEntry);
}

/** Drafts belong to a project/shot/candidate, never to the currently visible form. */
export function useVisualIntentDraft(
  projectId: string | undefined,
  shotId: string | undefined,
  assetId: string,
  baseId: string | undefined,
  saved: IntentDraft,
  baseCanonicalRevision?: number,
  serverDraftsEnabled = false,
  quiescence?: ProjectDraftQuiescence,
) {
  const [drafts, setDrafts] = useState<Drafts>(readDrafts);
  useMediaDraftErasure(storageKey, setDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const [serverRevision, setServerRevision] = useState(0);
  const [serverReady, setServerReady] = useState(false);
  const [serverConflict, setServerConflict] = useState(false);
  const writerStates = useRef(new Map<string, DurableWriterState>());
  const key = JSON.stringify([projectId, shotId, assetId]);
  const entityId = `${shotId ?? "unsaved"}:${assetId}`;
  const writerKey = JSON.stringify([projectId, entityId]);
  const activeWriterKey = useRef(writerKey);
  activeWriterKey.current = writerKey;
  const writerState = durableWriterStateFor(writerStates.current, writerKey);
  const entry = drafts[key];
  const value = entry?.value ?? saved;
  const inputPayload = (buffer: Entry) => ({ assetId, shotId, role: "shot_keyframe", identityIntent: buffer.value.identityIntent || null,
    compositionIntent: buffer.value.compositionIntent || null, styleIntent: buffer.value.styleIntent || null,
    sourceRefs: buffer.value.sourceRefs.split("\n").map(item => item.trim()).filter(Boolean), sourceRefsText: buffer.value.sourceRefs,
    ...(buffer.value.sourceBindingId ? { sourceBindingId: buffer.value.sourceBindingId } : {}),
    ...(buffer.value.retainedVisualIntentId ? { retainedVisualIntentId: buffer.value.retainedVisualIntentId } : {}) });

  const retained = useRetainedMediaJournal({ namespace: storageKey, key, projectId, entries: drafts, setEntries: setDrafts,
    serverRevision, serverReady, quiescence, validate: isIntentDraftEntry, basisMatches: candidate => candidate.baseId === (baseId ?? null) });
  const stale = Boolean(entry && entry.baseId !== (baseId ?? null) || !entry && retained.retained);
  const dirty = Boolean(entry && (stale || fields.some((field) => entry.value[field] !== saved[field])));

  useEffect(() => {
    try {
      clientJournalStorage.setItem(storageKey, JSON.stringify(drafts));
      setStorageFailed(false);
    } catch { setStorageFailed(true); }
  }, [drafts]);
  // This is deliberately a narrow projection of the form values, not a
  // session/UI snapshot.  The project ID and canonical storyboard revision
  // must exist before a durable server draft is created.
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision) {
      writerState.requestEpoch += 1;
      writerState.persistence = undefined;
      writerState.serverReady = false;
      if (activeWriterKey.current === writerKey) setServerReady(false);
      return;
    }
    writerState.serverRevision = 0;
    writerState.abandoning = false;
    writerState.acknowledgedPayload = undefined;
    writerState.persistence = undefined;
    writerState.serverConflict = false;
    const epoch = ++writerState.requestEpoch;
    writerState.serverReady = false;
    if (activeWriterKey.current === writerKey) {
      setServerRevision(0);
      setServerConflict(false);
      setServerReady(false);
    }
    let cancelled = false;
    void plotloomApi.getAuthoringDrafts(projectId).then((items) => {
      if (cancelled || writerState.requestEpoch !== epoch) return;
      const remote = items.find((item) => item.editorScope === "visual_intent" && item.entityId === entityId);
      if (remote) {
        const payload = remote.payload as Partial<{ assetId: string; shotId: string; identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string[]; sourceRefsText?: string; sourceBindingId: string; retainedVisualIntentId: string }>;
        if (payload.assetId === assetId && payload.shotId === shotId && Array.isArray(payload.sourceRefs)) {
          const sourceRefs = payload.sourceRefs;
          setDrafts((current) => current[key] ? current : {
            ...current,
            [key]: {
              baseId: baseId ?? null,
              value: {
                identityIntent: payload.identityIntent ?? "",
                compositionIntent: payload.compositionIntent ?? "",
                styleIntent: payload.styleIntent ?? "",
                sourceRefs: payload.sourceRefsText ?? sourceRefs.join("\n"),
                sourceBindingId: payload.sourceBindingId,
                retainedVisualIntentId: payload.retainedVisualIntentId,
              },
            },
          });
          writerState.serverRevision = remote.draftRevision;
          writerState.acknowledgedPayload = JSON.stringify({
            assetId,
            shotId,
            role: "shot_keyframe",
            identityIntent: payload.identityIntent ?? null,
            compositionIntent: payload.compositionIntent ?? null,
            styleIntent: payload.styleIntent ?? null,
            sourceRefs,
            sourceRefsText: payload.sourceRefsText ?? sourceRefs.join("\n"),
            ...(payload.sourceBindingId ? { sourceBindingId: payload.sourceBindingId } : {}),
            ...(payload.retainedVisualIntentId ? { retainedVisualIntentId: payload.retainedVisualIntentId } : {}),
          });
          if (remote.baseCanonicalRevision === baseCanonicalRevision) retained.acknowledge(remote.draftRevision, candidate => JSON.stringify(inputPayload(candidate)) === writerState.acknowledgedPayload);
          if (activeWriterKey.current === writerKey) setServerRevision(remote.draftRevision);
        }
      }
      const localEntry = drafts[key];
      if (localEntry) {
        const samePayload = JSON.stringify(inputPayload(localEntry)) === writerState.acknowledgedPayload;
        const exactReceipt = remote && samePayload && (localEntry.expectedDraftRevision === undefined || localEntry.expectedDraftRevision + 1 === remote.draftRevision);
        if (exactReceipt) setDrafts(current => current[key] === localEntry ? { ...current, [key]: { ...localEntry, expectedDraftRevision: remote.draftRevision } } : current);
        else if (localEntry.ownershipConflict || (localEntry.expectedDraftRevision ?? 0) !== (remote?.draftRevision ?? 0)) {
          writerState.serverConflict = true;
          if (activeWriterKey.current === writerKey) setServerConflict(true);
        }
      }
      writerState.serverReady = true;
      if (activeWriterKey.current === writerKey) setServerReady(true);
    }).catch(() => {
      // Keep the local buffer, but do not write without an authoritative
      // draft read and its CAS receipt.
      if (!cancelled && writerState.requestEpoch === epoch) {
        writerState.serverReady = false;
        if (activeWriterKey.current === writerKey) setServerReady(false);
      }
    });
    return () => { cancelled = true; };
  }, [activeWriterKey, assetId, baseCanonicalRevision, baseId, entityId, key, projectId, serverDraftsEnabled, shotId, writerKey, writerState]);
  const flush = useCallback(async (): Promise<boolean> => {
    if (projectId && quiescence && !quiescence.canWrite(projectId)) return false;
    if (writerState.abandoning || writerState.suspended || entry?.ownershipConflict) return false;
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry) return true;
    if (writerState.timer !== undefined) {
      window.clearTimeout(writerState.timer);
      writerState.timer = undefined;
    }
    if (!writerState.serverReady || writerState.serverConflict) return false;
    const existing = writerState.persistence;
    if (existing) await existing;
    if (quiescence && !quiescence.canWrite(projectId)) return false;
    if (writerState.abandoning || writerState.suspended || entry?.ownershipConflict) return false;
    if (writerState.serverConflict) return false;
    const payload = inputPayload(entry);
    const fingerprint = JSON.stringify(payload);

    if (writerState.acknowledgedPayload === fingerprint) return true;
    const epoch = writerState.requestEpoch;
    const persistence = saveWorkingDraft(projectId, {
      editorScope: "visual_intent", entityId, baseCanonicalRevision,
      expectedDraftRevision: writerState.serverRevision, payload,
    }).then((receipt) => {
      if (writerState.requestEpoch !== epoch) return false;
      writerState.serverRevision = receipt.draftRevision;
      setDrafts(current => current[key] ? { ...current, [key]: { ...current[key], expectedDraftRevision: receipt.draftRevision } } : current);
      writerState.acknowledgedPayload = fingerprint;
      writerState.serverConflict = false;
      if (activeWriterKey.current === writerKey) {
        setServerRevision(receipt.draftRevision);
        setServerConflict(false);
      }
      return true;
    }).catch(error => {
      if (writerState.requestEpoch === epoch) {
        writerState.serverConflict = error instanceof ApiError && error.status === 409;
        if (activeWriterKey.current === writerKey) setServerConflict(writerState.serverConflict);
      }
      return false;
    });
    const pendingPersistence = persistence.then(() => undefined);
    writerState.persistence = pendingPersistence;
    const saved = await persistence;
    if (writerState.persistence === pendingPersistence) writerState.persistence = undefined;
    return saved;
  }, [activeWriterKey, assetId, baseCanonicalRevision, dirty, entityId, entry, projectId, quiescence, serverDraftsEnabled, shotId, writerKey, writerState]);
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry || !serverReady || serverConflict) return;
    writerState.timer = window.setTimeout(() => {
      writerState.timer = undefined;
      void flush();
    }, 750);
    return () => {
      if (writerState.timer !== undefined) window.clearTimeout(writerState.timer);
      writerState.timer = undefined;
    };
  }, [assetId, baseCanonicalRevision, entry, flush, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId, writerState]);
  useEffect(() => {
    if (!quiescence || !serverDraftsEnabled || !projectId || !shotId || !assetId) return;
    // A dirty draft remains an admitted project writer when its particular
    // form unmounts. Switching shots must not hide it from a later Close.
    return quiescence.register(projectId, `visual_intent:${entityId}`, flush, {
      pending: () => Boolean(entry && (writerState.serverConflict || !writerState.serverReady || writerState.acknowledgedPayload !== JSON.stringify(inputPayload(entry)))),
      locallyPreserved: () => !storageFailed,
      retainOnUnmount: Boolean(entry),
      suspendWrites: async () => {
        writerState.suspended = true;
        if (writerState.timer !== undefined) window.clearTimeout(writerState.timer);
        writerState.timer = undefined;
        await writerState.persistence;
        return () => {
          writerState.suspended = false;
          if (!writerState.abandoning && quiescence.canWrite(projectId)) writerState.timer = window.setTimeout(() => { writerState.timer = undefined; void flush(); }, 750);
        };
      },
      discardUnsent: async () => {
        writerState.abandoning = true;
        if (writerState.timer !== undefined) window.clearTimeout(writerState.timer);
        writerState.timer = undefined;
        await writerState.persistence;
        writerState.requestEpoch += 1;
        discardMediaDraftEntry(storageKey, key);
      },
    });
  }, [assetId, dirty, entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId, storageFailed]);
  useEffect(() => {
    if (!storageFailed || !Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts, storageFailed]);

  const clearWithDisposition = async (consumed: boolean): Promise<boolean> => {
    const buffered = entry;
    if (!buffered) return true;
    await writerState.persistence;
    if (projectId && quiescence && !quiescence.canWrite(projectId)) return false;
    const removeBuffered = () => setDrafts((current) => {
      if (current[key] !== buffered) return current;
      clientJournalStorage.discardCurrentEntry(storageKey, key, buffered);
      const next = { ...current };
      delete next[key];
      return next;
    });
    const matchesReceipt = writerState.acknowledgedPayload === JSON.stringify(inputPayload(buffered));
    if (!serverDraftsEnabled || !projectId || consumed || !writerState.serverRevision) {
      if (consumed && matchesReceipt) {
        writerState.serverRevision = 0;
        writerState.acknowledgedPayload = undefined;
        setServerRevision(0);
      }
      removeBuffered();
      return true;
    }
    if (!matchesReceipt) return false;
    const expectedDraftRevision = writerState.serverRevision;
    try {
      const receipt = await plotloomApi.discardAuthoringDraft(projectId, {
        editorScope: "visual_intent", entityId, expectedDraftRevision,
      });
      if (receipt !== expectedDraftRevision) throw new Error("visual intent draft changed before discard");
      writerState.serverRevision = 0;
      writerState.acknowledgedPayload = undefined;
      setServerRevision(0);
      removeBuffered();
      return true;
    } catch {
      writerState.serverConflict = true;
      setServerConflict(true);
      return false;
    }
  };
  const clear = () => clearWithDisposition(false);
  const clearConsumed = () => clearWithDisposition(true);
  const update = (change: (current: IntentDraft) => IntentDraft) => {
    if (!projectId || !shotId || !assetId || quiescence?.isClosing(projectId) || (quiescence && !quiescence.canWrite(projectId))) return;
    setDrafts((current) => ({ ...current, [key]: {
      baseId: current[key] ? current[key].baseId : baseId ?? null,
      expectedDraftRevision: current[key]?.expectedDraftRevision ?? writerState.serverRevision,
      value: change(current[key]?.value ?? saved),
    } }));
  };
  return { value, update, clear, clearConsumed, flush, dirty, stale, storageFailed, serverConflict, serverReady, serverRevision, retainedNotice: retained.notice };
}
export {
  imageJobTargetId,
  useImageJobDirectionDraft,
  type ImageJobDraftTarget,
} from "./image-job-direction-drafts";
