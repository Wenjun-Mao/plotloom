import { useRetainedMediaJournal } from "./features/authoring/useRetainedMediaJournal";
import { saveWorkingDraft } from "./features/authoring/saveWorkingDraft";
import { clientJournalStorage } from "./features/authoring/clientJournalStorage";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, plotloomApi } from "./api";
import type { ProjectDraftQuiescence } from "./features/authoring/projectDraftQuiescence";
import { discardMediaDraftEntry, useMediaDraftErasure } from "./features/authoring/projectDraftCache";

export type ImageJobDraftTarget =
  | { kind: "original"; sceneContinuityBindingId?: string }
  | { kind: "refinement"; parentCandidateAssetId: string }
  | { kind: "keyframe_adaptation"; profileId: string; profileLabel: string };

type ImageJobDraftEntry = { contextId: string; value: string; expectedDraftRevision?: number; ownershipConflict?: boolean };
type ImageJobDrafts = Record<string, ImageJobDraftEntry>;
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
const imageJobStorageKey = "plotloom:image-job-direction-drafts:v1";

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

function readImageJobDrafts(): ImageJobDrafts {
  try {
    const value: unknown = JSON.parse(clientJournalStorage.getItem(imageJobStorageKey) ?? "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, ImageJobDraftEntry] => {
      const candidate = entry[1] as Partial<ImageJobDraftEntry> | undefined;
      return typeof candidate?.contextId === "string" && typeof candidate.value === "string";
    }));
  } catch { return {}; }
}

export function imageJobTargetId(target: ImageJobDraftTarget): string {
  if (target.kind === "refinement") return `refinement:${target.parentCandidateAssetId}`;
  if (target.kind === "keyframe_adaptation") return `keyframe_adaptation:${target.profileId}`;
  if (target.sceneContinuityBindingId) return `scene_continuity:${target.sceneContinuityBindingId}`;
  return "original";
}

/** Owns one exact manual image-job direction and its durable CAS receipt. */
export function useImageJobDirectionDraft(
  projectId: string | undefined,
  shotId: string | undefined,
  target: ImageJobDraftTarget,
  contextId: string,
  baseCanonicalRevision?: number,
  serverDraftsEnabled = false,
  quiescence?: ProjectDraftQuiescence,
  readOnly = false,
) {
  const [drafts, setDrafts] = useState<ImageJobDrafts>(readImageJobDrafts);
  useMediaDraftErasure(imageJobStorageKey, setDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const [serverRevision, setServerRevision] = useState(0);
  const [serverReady, setServerReady] = useState(false);
  const [serverConflict, setServerConflict] = useState(false);
  const writerStates = useRef(new Map<string, DurableWriterState>());
  const targetId = imageJobTargetId(target);
  const key = JSON.stringify([projectId, shotId, targetId]);
  const entityId = `${shotId ?? "unsaved"}:${targetId}`;
  const writerKey = JSON.stringify([projectId, entityId]);
  const activeWriterKey = useRef(writerKey);
  activeWriterKey.current = writerKey;
  const writerState = durableWriterStateFor(writerStates.current, writerKey);
  const entry = drafts[key];
  const recoveryOwner = useRef({ key, contextId, entry, readOnly });
  recoveryOwner.current = { key, contextId, entry, readOnly };
  const ownsEditableEntry = () => recoveryOwner.current.key === key
    && recoveryOwner.current.contextId === contextId && recoveryOwner.current.entry === entry
    && !recoveryOwner.current.readOnly && !writerState.abandoning && !writerState.suspended
    && (!projectId || !quiescence || !quiescence.isClosing(projectId) && quiescence.canWrite(projectId));
  const mayRecoverCurrentEntry = () => Boolean(entry && entry.contextId !== contextId && ownsEditableEntry()
    && (!serverDraftsEnabled || writerState.serverReady && !writerState.serverConflict));
  const canRecover = mayRecoverCurrentEntry();
  const retained = useRetainedMediaJournal({ namespace: imageJobStorageKey, key, projectId, entries: drafts, setEntries: setDrafts,
    serverRevision, serverReady, quiescence,
    validate: (value: unknown): value is ImageJobDraftEntry => Boolean(value && typeof value === "object" && typeof (value as ImageJobDraftEntry).value === "string" && typeof (value as ImageJobDraftEntry).contextId === "string"),
    basisMatches: candidate => candidate.contextId === contextId });
  const stale = Boolean(entry && entry.contextId !== contextId || !entry && retained.retained);
  const value = entry?.value ?? "";
  const dirty = Boolean(entry && (entry.value.trim() || (serverDraftsEnabled && (serverRevision > 0 || !serverReady))));

  useEffect(() => {
    try {
      clientJournalStorage.setItem(imageJobStorageKey, JSON.stringify(drafts));
      setStorageFailed(false);
    } catch { setStorageFailed(true); }
  }, [drafts]);
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision) {
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
      const remote = items.find((item) => item.editorScope === "image_direction" && item.entityId === entityId);
      if (remote) {
        const payload = remote.payload as Partial<{ shotId: string; targetId: string; contextId: string; presentationChange: string }>;
        if (payload.shotId === shotId && payload.targetId === targetId && typeof payload.presentationChange === "string") {
          const presentationChange = payload.presentationChange;
          setDrafts((current) => current[key] ? current : { ...current, [key]: { contextId: payload.contextId ?? contextId, value: presentationChange } });
          writerState.serverRevision = remote.draftRevision;
          writerState.acknowledgedPayload = JSON.stringify({ shotId, targetId, contextId: payload.contextId ?? contextId, presentationChange });
          if (remote.baseCanonicalRevision === baseCanonicalRevision) retained.acknowledge(remote.draftRevision, candidate => JSON.stringify({ shotId, targetId, contextId: candidate.contextId, presentationChange: candidate.value }) === writerState.acknowledgedPayload);
          if (activeWriterKey.current === writerKey) setServerRevision(remote.draftRevision);
        }
      }
      const localEntry = drafts[key];
      if (localEntry) {
        const samePayload = JSON.stringify({ shotId, targetId, contextId: localEntry.contextId, presentationChange: localEntry.value }) === writerState.acknowledgedPayload;
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
      if (!cancelled && writerState.requestEpoch === epoch) {
        writerState.serverReady = false;
        if (activeWriterKey.current === writerKey) setServerReady(false);
      }
    });
    return () => { cancelled = true; };
  }, [activeWriterKey, baseCanonicalRevision, contextId, entityId, key, projectId, serverDraftsEnabled, shotId, targetId, writerKey, writerState]);

  const flush = useCallback(async (): Promise<boolean> => {
    if (projectId && quiescence && !quiescence.canWrite(projectId)) return false;
    if (writerState.abandoning || writerState.suspended || entry?.ownershipConflict) return false;
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry) return true;
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
    const payload = { shotId, targetId, contextId: entry.contextId, presentationChange: entry.value };
    const fingerprint = JSON.stringify(payload);
    if (writerState.acknowledgedPayload === fingerprint) return true;
    const epoch = writerState.requestEpoch;
    const persistence = saveWorkingDraft(projectId, {
      editorScope: "image_direction", entityId, baseCanonicalRevision,
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
  }, [activeWriterKey, baseCanonicalRevision, entityId, entry, projectId, quiescence, serverDraftsEnabled, shotId, targetId, writerKey, writerState]);

  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry || !serverReady || serverConflict) return;
    writerState.timer = window.setTimeout(() => {
      writerState.timer = undefined;
      void flush();
    }, 750);
    return () => {
      if (writerState.timer !== undefined) window.clearTimeout(writerState.timer);
      writerState.timer = undefined;
    };
  }, [baseCanonicalRevision, entry, flush, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId, writerState]);
  useEffect(() => {
    if (!quiescence || !serverDraftsEnabled || !projectId || !shotId) return;
    return quiescence.register(projectId, `image_direction:${entityId}`, flush, {
      pending: () => Boolean(entry && (writerState.serverConflict || !writerState.serverReady || writerState.acknowledgedPayload !== JSON.stringify({ shotId, targetId, contextId: entry.contextId, presentationChange: entry.value }))),
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
        discardMediaDraftEntry(imageJobStorageKey, key);
      },
    });
  }, [dirty, entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId, storageFailed]);
  useEffect(() => {
    if (!storageFailed || !Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts, storageFailed]);

  const update = (next: string) => {
    if (!projectId || !shotId || quiescence?.isClosing(projectId) || (quiescence && !quiescence.canWrite(projectId))) return;
    setDrafts((current) => {
      return { ...current, [key]: { contextId: current[key]?.contextId ?? contextId, expectedDraftRevision: current[key]?.expectedDraftRevision ?? writerState.serverRevision, value: next } };
    });
  };
  const clearWithDisposition = async (consumed: boolean): Promise<boolean> => {
    if (!consumed && !ownsEditableEntry()) return false;
    const buffered = entry;
    if (!buffered) return true;
    await writerState.persistence;
    if (!consumed && !ownsEditableEntry() || projectId && quiescence && !quiescence.canWrite(projectId)) return false;
    const removeBuffered = () => setDrafts((current) => {
      if (current[key] !== buffered) return current;
      clientJournalStorage.discardCurrentEntry(imageJobStorageKey, key, buffered);
      const next = { ...current };
      delete next[key];
      return next;
    });
    const matchesReceipt = writerState.acknowledgedPayload === JSON.stringify({ shotId, targetId, contextId: buffered.contextId, presentationChange: buffered.value });
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
        editorScope: "image_direction", entityId, expectedDraftRevision,
      });
      if (receipt !== expectedDraftRevision) throw new Error("image direction draft changed before discard");
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
  const recoverForCurrentContext = () => {
    // A retained-only warning is not a loaded current entry. Captured callbacks
    // cannot recover across hydration, ownership or admission changes.
    if (!entry || !mayRecoverCurrentEntry()) return false;
    setDrafts(current => current[key] === entry && mayRecoverCurrentEntry()
      ? { ...current, [key]: { ...entry, contextId } } : current);
    return true;
  };

  return { value, update, clear, clearConsumed, flush, recoverForCurrentContext, canRecover, hasCurrentEntry: Boolean(entry), dirty, stale, storageFailed, targetId, serverConflict, serverReady, serverRevision, retainedNotice: retained.notice };
}
