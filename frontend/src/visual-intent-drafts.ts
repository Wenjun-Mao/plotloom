import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { ProjectDraftQuiescence } from "./features/authoring/projectDraftQuiescence";

export type IntentDraft = { identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string };
type Entry = { baseId: string | null; value: IntentDraft };
type Drafts = Record<string, Entry>;
type DurableWriterState = {
  serverRevision: number;
  acknowledgedPayload?: string;
  persistence?: Promise<void>;
  timer?: number;
  serverReady: boolean;
  serverConflict: boolean;
  requestEpoch: number;
};
const storageKey = "plotloom:visual-intent-drafts:v1";
const fields = ["identityIntent", "compositionIntent", "styleIntent", "sourceRefs"] as const;

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
    const value: unknown = JSON.parse(window.sessionStorage.getItem(key) ?? "{}");
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
    && fields.every((field) => typeof entry.value?.[field] === "string");
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
  const stale = Boolean(entry && entry.baseId !== (baseId ?? null));
  const dirty = Boolean(entry && (stale || fields.some((field) => entry.value[field] !== saved[field])));

  useEffect(() => {
    try {
      window.sessionStorage.setItem(storageKey, JSON.stringify(drafts));
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
        const payload = remote.payload as Partial<{ assetId: string; shotId: string; identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string[] }>;
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
                sourceRefs: sourceRefs.join("\n"),
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
          });
          if (activeWriterKey.current === writerKey) setServerRevision(remote.draftRevision);
        }
      }
      writerState.serverReady = true;
      if (activeWriterKey.current === writerKey) setServerReady(true);
    }).catch(() => {
      // The retained runtime has no media draft route until storage cutover.
      // Keep the existing local safety buffer there; direct storage still
      // requires the acknowledged server receipt when the route is available.
      if (!cancelled && writerState.requestEpoch === epoch) {
        writerState.serverReady = false;
        if (activeWriterKey.current === writerKey) setServerReady(false);
      }
    });
    return () => { cancelled = true; };
  }, [activeWriterKey, assetId, baseCanonicalRevision, baseId, entityId, key, projectId, serverDraftsEnabled, shotId, writerKey, writerState]);
  const flush = useCallback(async (): Promise<boolean> => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry) return true;
    if (writerState.timer !== undefined) {
      window.clearTimeout(writerState.timer);
      writerState.timer = undefined;
    }
    if (!writerState.serverReady || writerState.serverConflict) return false;
    const existing = writerState.persistence;
    if (existing) await existing;
    if (writerState.serverConflict) return false;
    const payload = {
      assetId,
      shotId,
      role: "shot_keyframe" as const,
      identityIntent: entry.value.identityIntent || null,
      compositionIntent: entry.value.compositionIntent || null,
      styleIntent: entry.value.styleIntent || null,
      sourceRefs: entry.value.sourceRefs.split("\n").map((item) => item.trim()).filter(Boolean),
    };
    const fingerprint = JSON.stringify(payload);
    // A visual intent without provenance cannot obtain a valid durable
    // receipt. It must block Close while dirty rather than reporting a false
    // drain and leaving the session-only edit behind a closed project.
    if (!payload.sourceRefs.length) return !dirty;
    if (writerState.acknowledgedPayload === fingerprint) return true;
    const epoch = writerState.requestEpoch;
    const persistence = plotloomApi.saveAuthoringDraft(projectId, {
      editorScope: "visual_intent", entityId, baseCanonicalRevision,
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
  }, [activeWriterKey, assetId, baseCanonicalRevision, dirty, entityId, entry, projectId, serverDraftsEnabled, shotId, writerKey, writerState]);
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
    return quiescence.register(projectId, `visual_intent:${entityId}`, flush, { retainOnUnmount: dirty });
  }, [assetId, dirty, entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId]);
  useEffect(() => {
    if (!Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts]);

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
    if (!projectId || !shotId || !assetId || quiescence?.isClosing(projectId)) return;
    setDrafts((current) => ({ ...current, [key]: {
      baseId: current[key] ? current[key].baseId : baseId ?? null,
      value: change(current[key]?.value ?? saved),
    } }));
  };
  return { value, update, clear, clearConsumed, flush, dirty, stale, storageFailed, serverConflict, serverReady, serverRevision };
}
export {
  imageJobTargetId,
  useImageJobDirectionDraft,
  type ImageJobDraftTarget,
} from "./image-job-direction-drafts";
