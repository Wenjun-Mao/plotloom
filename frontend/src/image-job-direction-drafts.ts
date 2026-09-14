import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { ProjectDraftQuiescence } from "./features/authoring/projectDraftQuiescence";

export type ImageJobDraftTarget =
  | { kind: "original" }
  | { kind: "refinement"; parentCandidateAssetId: string }
  | { kind: "keyframe_adaptation"; profileId: string; profileLabel: string };

type ImageJobDraftEntry = { contextId: string; value: string };
type ImageJobDrafts = Record<string, ImageJobDraftEntry>;
type DurableWriterState = {
  serverRevision: number;
  acknowledgedPayload?: string;
  persistence?: Promise<void>;
  timer?: number;
  serverReady: boolean;
  serverConflict: boolean;
  requestEpoch: number;
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
    const value: unknown = JSON.parse(window.sessionStorage.getItem(imageJobStorageKey) ?? "{}");
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
) {
  const [drafts, setDrafts] = useState<ImageJobDrafts>(readImageJobDrafts);
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
  const stale = Boolean(entry && entry.contextId !== contextId);
  const value = entry?.value ?? "";
  const dirty = Boolean(entry && (entry.value.trim() || (serverDraftsEnabled && (serverRevision > 0 || !serverReady))));

  useEffect(() => {
    try {
      window.sessionStorage.setItem(imageJobStorageKey, JSON.stringify(drafts));
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
          if (activeWriterKey.current === writerKey) setServerRevision(remote.draftRevision);
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
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry) return true;
    if (writerState.timer !== undefined) {
      window.clearTimeout(writerState.timer);
      writerState.timer = undefined;
    }
    if (!writerState.serverReady || writerState.serverConflict) return false;
    const existing = writerState.persistence;
    if (existing) await existing;
    if (writerState.serverConflict) return false;
    if (!entry.value.trim()) {
      const expectedDraftRevision = writerState.serverRevision;
      if (!expectedDraftRevision) {
        setDrafts((current) => {
          if (current[key] !== entry) return current;
          const next = { ...current };
          delete next[key];
          return next;
        });
        return true;
      }
      const epoch = writerState.requestEpoch;
      const deletion = plotloomApi.discardAuthoringDraft(projectId, {
        editorScope: "image_direction", entityId, expectedDraftRevision,
      }).then((receipt) => {
        if (writerState.requestEpoch !== epoch || receipt !== expectedDraftRevision) return false;
        writerState.serverRevision = 0;
        writerState.acknowledgedPayload = undefined;
        if (activeWriterKey.current === writerKey) setServerRevision(0);
        setDrafts((current) => {
          if (current[key] !== entry) return current;
          const next = { ...current };
          delete next[key];
          return next;
        });
        return true;
      }).catch(() => {
        if (writerState.requestEpoch === epoch) {
          writerState.serverConflict = true;
          if (activeWriterKey.current === writerKey) setServerConflict(true);
        }
        return false;
      });
      const pendingDeletion = deletion.then(() => undefined);
      writerState.persistence = pendingDeletion;
      const discarded = await deletion;
      if (writerState.persistence === pendingDeletion) writerState.persistence = undefined;
      return discarded;
    }
    const payload = { shotId, targetId, contextId: entry.contextId, presentationChange: entry.value };
    const fingerprint = JSON.stringify(payload);
    if (writerState.acknowledgedPayload === fingerprint) return true;
    const epoch = writerState.requestEpoch;
    const persistence = plotloomApi.saveAuthoringDraft(projectId, {
      editorScope: "image_direction", entityId, baseCanonicalRevision,
      expectedDraftRevision: writerState.serverRevision, payload,
    }).then((receipt) => {
      if (writerState.requestEpoch !== epoch) return false;
      writerState.serverRevision = receipt.draftRevision;
      writerState.acknowledgedPayload = fingerprint;
      writerState.serverConflict = false;
      if (activeWriterKey.current === writerKey) {
        setServerRevision(receipt.draftRevision);
        setServerConflict(false);
      }
      return true;
    }).catch(() => {
      if (writerState.requestEpoch === epoch) {
        writerState.serverConflict = true;
        if (activeWriterKey.current === writerKey) setServerConflict(true);
      }
      return false;
    });
    const pendingPersistence = persistence.then(() => undefined);
    writerState.persistence = pendingPersistence;
    const saved = await persistence;
    if (writerState.persistence === pendingPersistence) writerState.persistence = undefined;
    return saved;
  }, [activeWriterKey, baseCanonicalRevision, entityId, entry, projectId, serverDraftsEnabled, shotId, targetId, writerKey, writerState]);

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
    return quiescence.register(projectId, `image_direction:${entityId}`, flush, { retainOnUnmount: dirty });
  }, [dirty, entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId]);
  useEffect(() => {
    if (!Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts]);

  const update = (next: string) => {
    if (!projectId || !shotId || quiescence?.isClosing(projectId)) return;
    setDrafts((current) => {
      if (!next.trim()) {
        // Before a durable draft exists, empty text is clean. Once the server
        // knows the direction, retain an empty marker for an exact CAS discard.
        if (!serverDraftsEnabled || (serverReady && !writerState.serverRevision)) {
          const cleaned = { ...current };
          delete cleaned[key];
          return cleaned;
        }
        return { ...current, [key]: { contextId: current[key]?.contextId ?? contextId, value: "" } };
      }
      return { ...current, [key]: { contextId: current[key]?.contextId ?? contextId, value: next } };
    });
  };
  const clearWithDisposition = async (consumed: boolean): Promise<boolean> => {
    const buffered = entry;
    if (!buffered) return true;
    await writerState.persistence;
    const removeBuffered = () => setDrafts((current) => {
      if (current[key] !== buffered) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
    if (!serverDraftsEnabled || !projectId || consumed || !writerState.serverRevision) {
      if (consumed) {
        writerState.serverRevision = 0;
        writerState.acknowledgedPayload = undefined;
        setServerRevision(0);
      }
      removeBuffered();
      return true;
    }
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
  const recoverForCurrentContext = () => setDrafts((current) => {
    const currentEntry = current[key];
    if (!currentEntry) return current;
    return { ...current, [key]: { ...currentEntry, contextId } };
  });

  return { value, update, clear, clearConsumed, flush, recoverForCurrentContext, dirty, stale, storageFailed, targetId, serverConflict, serverReady, serverRevision };
}
