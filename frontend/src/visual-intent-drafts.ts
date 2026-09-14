import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { ProjectDraftQuiescence } from "./features/authoring/projectDraftQuiescence";

export type IntentDraft = { identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string };
type Entry = { baseId: string | null; value: IntentDraft };
type Drafts = Record<string, Entry>;
const storageKey = "plotloom:visual-intent-drafts:v1";
const imageJobStorageKey = "plotloom:image-job-direction-drafts:v1";
const fields = ["identityIntent", "compositionIntent", "styleIntent", "sourceRefs"] as const;

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
  const serverRevisionRef = useRef(0);
  const acknowledgedPayloadRef = useRef<string | undefined>(undefined);
  const persistenceRef = useRef<Promise<void> | undefined>(undefined);
  const timerRef = useRef<number | undefined>(undefined);
  const [serverReady, setServerReady] = useState(false);
  const [serverConflict, setServerConflict] = useState(false);
  const serverConflictRef = useRef(false);
  const requestEpochRef = useRef(0);
  const key = JSON.stringify([projectId, shotId, assetId]);
  const entityId = `${shotId ?? "unsaved"}:${assetId}`;
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
      requestEpochRef.current += 1;
      persistenceRef.current = undefined;
      setServerReady(false);
      return;
    }
    serverRevisionRef.current = 0;
    acknowledgedPayloadRef.current = undefined;
    persistenceRef.current = undefined;
    setServerRevision(0);
    serverConflictRef.current = false;
    setServerConflict(false);
    const epoch = ++requestEpochRef.current;
    setServerReady(false);
    let cancelled = false;
    void plotloomApi.getAuthoringDrafts(projectId).then((items) => {
      if (cancelled || requestEpochRef.current !== epoch) return;
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
          serverRevisionRef.current = remote.draftRevision;
          acknowledgedPayloadRef.current = JSON.stringify({
            assetId,
            shotId,
            role: "shot_keyframe",
            identityIntent: payload.identityIntent ?? null,
            compositionIntent: payload.compositionIntent ?? null,
            styleIntent: payload.styleIntent ?? null,
            sourceRefs,
          });
          setServerRevision(remote.draftRevision);
        }
      }
      setServerReady(true);
    }).catch(() => {
      // The retained runtime has no media draft route until storage cutover.
      // Keep the existing local safety buffer there; direct storage still
      // requires the acknowledged server receipt when the route is available.
      if (!cancelled && requestEpochRef.current === epoch) setServerReady(false);
    });
    return () => { cancelled = true; };
  }, [assetId, baseCanonicalRevision, baseId, entityId, key, projectId, serverDraftsEnabled, shotId]);
  const flush = useCallback(async (): Promise<boolean> => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry) return true;
    if (timerRef.current !== undefined) {
      window.clearTimeout(timerRef.current);
      timerRef.current = undefined;
    }
    if (!serverReady || serverConflictRef.current) return false;
    const existing = persistenceRef.current;
    if (existing) await existing;
    if (serverConflictRef.current) return false;
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
    if (acknowledgedPayloadRef.current === fingerprint) return true;
    const epoch = requestEpochRef.current;
    const persistence = plotloomApi.saveAuthoringDraft(projectId, {
      editorScope: "visual_intent", entityId, baseCanonicalRevision,
      expectedDraftRevision: serverRevisionRef.current, payload,
    }).then((receipt) => {
      if (requestEpochRef.current !== epoch) return false;
      serverRevisionRef.current = receipt.draftRevision;
      acknowledgedPayloadRef.current = fingerprint;
      setServerRevision(receipt.draftRevision);
      serverConflictRef.current = false;
      setServerConflict(false);
      return true;
    }).catch(() => {
      if (requestEpochRef.current === epoch) {
        serverConflictRef.current = true;
        setServerConflict(true);
      }
      return false;
    });
    persistenceRef.current = persistence.then(() => undefined);
    const saved = await persistence;
    if (persistenceRef.current) persistenceRef.current = undefined;
    return saved;
  }, [assetId, baseCanonicalRevision, dirty, entityId, entry, projectId, serverDraftsEnabled, serverReady, shotId]);
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry || !serverReady || serverConflict) return;
    timerRef.current = window.setTimeout(() => {
      timerRef.current = undefined;
      void flush();
    }, 750);
    return () => {
      if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
      timerRef.current = undefined;
    };
  }, [assetId, baseCanonicalRevision, entry, flush, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId]);
  useEffect(() => {
    if (!quiescence || !serverDraftsEnabled || !projectId || !shotId || !assetId) return;
    return quiescence.register(projectId, `visual_intent:${entityId}`, flush);
  }, [assetId, entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId]);
  useEffect(() => {
    if (!Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts]);

  const clear = async () => {
    setDrafts((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    await persistenceRef.current;
    if (serverDraftsEnabled && projectId && serverRevisionRef.current && !serverConflictRef.current) {
      await plotloomApi.discardAuthoringDraft(projectId, {
        editorScope: "visual_intent", entityId, expectedDraftRevision: serverRevisionRef.current,
      }).then(() => {
        serverRevisionRef.current = 0;
        acknowledgedPayloadRef.current = undefined;
        setServerRevision(0);
      }).catch(() => setServerConflict(true));
    }
  };
  const update = (change: (current: IntentDraft) => IntentDraft) => {
    if (!projectId || !shotId || !assetId) return;
    setDrafts((current) => ({ ...current, [key]: {
      baseId: current[key] ? current[key].baseId : baseId ?? null,
      value: change(current[key]?.value ?? saved),
    } }));
  };
  return { value, update, clear, flush, dirty, stale, storageFailed, serverConflict, serverReady, serverRevision };
}

export type ImageJobDraftTarget =
  | { kind: "original" }
  | { kind: "refinement"; parentCandidateAssetId: string }
  | { kind: "keyframe_adaptation"; profileId: string; profileLabel: string };

type ImageJobDraftEntry = { contextId: string; value: string };
type ImageJobDrafts = Record<string, ImageJobDraftEntry>;

function isImageJobDraftEntry(value: unknown): value is ImageJobDraftEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as Partial<ImageJobDraftEntry>;
  return typeof entry.contextId === "string" && typeof entry.value === "string";
}

function readImageJobDrafts(): ImageJobDrafts {
  return readSessionDrafts(imageJobStorageKey, isImageJobDraftEntry);
}

export function imageJobTargetId(target: ImageJobDraftTarget): string {
  if (target.kind === "refinement") return `refinement:${target.parentCandidateAssetId}`;
  if (target.kind === "keyframe_adaptation") return `keyframe_adaptation:${target.profileId}`;
  return "original";
}

/**
 * A direction belongs to the exact manual-job target and approved context. It
 * is session-only, so changing shots or returning after navigation can never
 * silently reuse a direction for another job.
 */
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
  const serverRevisionRef = useRef(0);
  const acknowledgedPayloadRef = useRef<string | undefined>(undefined);
  const persistenceRef = useRef<Promise<void> | undefined>(undefined);
  const timerRef = useRef<number | undefined>(undefined);
  const [serverReady, setServerReady] = useState(false);
  const [serverConflict, setServerConflict] = useState(false);
  const serverConflictRef = useRef(false);
  const requestEpochRef = useRef(0);
  const targetId = imageJobTargetId(target);
  const key = JSON.stringify([projectId, shotId, targetId]);
  const entityId = `${shotId ?? "unsaved"}:${targetId}`;
  const entry = drafts[key];
  const stale = Boolean(entry && entry.contextId !== contextId);
  const value = entry?.value ?? "";

  useEffect(() => {
    try {
      window.sessionStorage.setItem(imageJobStorageKey, JSON.stringify(drafts));
      setStorageFailed(false);
    } catch { setStorageFailed(true); }
  }, [drafts]);
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision) {
      requestEpochRef.current += 1;
      persistenceRef.current = undefined;
      setServerReady(false);
      return;
    }
    serverRevisionRef.current = 0;
    acknowledgedPayloadRef.current = undefined;
    persistenceRef.current = undefined;
    setServerRevision(0);
    serverConflictRef.current = false;
    setServerConflict(false);
    const epoch = ++requestEpochRef.current;
    setServerReady(false);
    let cancelled = false;
    void plotloomApi.getAuthoringDrafts(projectId).then((items) => {
      if (cancelled || requestEpochRef.current !== epoch) return;
      const remote = items.find((item) => item.editorScope === "image_direction" && item.entityId === entityId);
      if (remote) {
        const payload = remote.payload as Partial<{ shotId: string; targetId: string; contextId: string; presentationChange: string }>;
        if (payload.shotId === shotId && payload.targetId === targetId && typeof payload.presentationChange === "string") {
          const presentationChange = payload.presentationChange;
          setDrafts((current) => current[key] ? current : { ...current, [key]: { contextId: payload.contextId ?? contextId, value: presentationChange } });
          serverRevisionRef.current = remote.draftRevision;
          acknowledgedPayloadRef.current = JSON.stringify({
            shotId,
            targetId,
            contextId: payload.contextId ?? contextId,
            presentationChange,
          });
          setServerRevision(remote.draftRevision);
        }
      }
      setServerReady(true);
    }).catch(() => {
      if (!cancelled && requestEpochRef.current === epoch) setServerReady(false);
    });
    return () => { cancelled = true; };
  }, [baseCanonicalRevision, contextId, entityId, key, projectId, serverDraftsEnabled, shotId, targetId]);
  const flush = useCallback(async (): Promise<boolean> => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry?.value.trim()) return true;
    if (timerRef.current !== undefined) {
      window.clearTimeout(timerRef.current);
      timerRef.current = undefined;
    }
    if (!serverReady || serverConflictRef.current) return false;
    const existing = persistenceRef.current;
    if (existing) await existing;
    if (serverConflictRef.current) return false;
    const payload = { shotId, targetId, contextId: entry.contextId, presentationChange: entry.value };
    const fingerprint = JSON.stringify(payload);
    if (acknowledgedPayloadRef.current === fingerprint) return true;
    const epoch = requestEpochRef.current;
    const persistence = plotloomApi.saveAuthoringDraft(projectId, {
      editorScope: "image_direction", entityId, baseCanonicalRevision,
      expectedDraftRevision: serverRevisionRef.current, payload,
    }).then((receipt) => {
      if (requestEpochRef.current !== epoch) return false;
      serverRevisionRef.current = receipt.draftRevision;
      acknowledgedPayloadRef.current = fingerprint;
      setServerRevision(receipt.draftRevision);
      serverConflictRef.current = false;
      setServerConflict(false);
      return true;
    }).catch(() => {
      if (requestEpochRef.current === epoch) {
        serverConflictRef.current = true;
        setServerConflict(true);
      }
      return false;
    });
    persistenceRef.current = persistence.then(() => undefined);
    const saved = await persistence;
    if (persistenceRef.current) persistenceRef.current = undefined;
    return saved;
  }, [baseCanonicalRevision, entityId, entry, projectId, serverDraftsEnabled, serverReady, shotId, targetId]);
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry?.value.trim() || !serverReady || serverConflict) return;
    timerRef.current = window.setTimeout(() => {
      timerRef.current = undefined;
      void flush();
    }, 750);
    return () => {
      if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
      timerRef.current = undefined;
    };
  }, [baseCanonicalRevision, entry, flush, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId]);
  useEffect(() => {
    if (!quiescence || !serverDraftsEnabled || !projectId || !shotId) return;
    return quiescence.register(projectId, `image_direction:${entityId}`, flush);
  }, [entityId, flush, projectId, quiescence, serverDraftsEnabled, shotId]);
  useEffect(() => {
    if (!Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts]);

  const update = (next: string) => {
    if (!projectId || !shotId) return;
    setDrafts((current) => {
      // Empty direction text is clean, not an unsent draft. Removing the
      // exact entry prevents an invisible value from retaining unload guards.
      if (!next.trim()) {
        const cleaned = { ...current };
        delete cleaned[key];
        return cleaned;
      }
      return { ...current, [key]: {
        contextId: current[key]?.contextId ?? contextId,
        value: next,
      } };
    });
  };
  const clear = async () => {
    setDrafts((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    await persistenceRef.current;
    if (serverDraftsEnabled && projectId && serverRevisionRef.current && !serverConflictRef.current) {
      await plotloomApi.discardAuthoringDraft(projectId, {
        editorScope: "image_direction", entityId, expectedDraftRevision: serverRevisionRef.current,
      }).then(() => {
        serverRevisionRef.current = 0;
        acknowledgedPayloadRef.current = undefined;
        setServerRevision(0);
      }).catch(() => setServerConflict(true));
    }
  };
  // Recovery is deliberate: it retains the text but rebases it only after the
  // creator has seen that its Approval, storyboard, or reviewed target changed.
  const recoverForCurrentContext = () => setDrafts((current) => {
    const currentEntry = current[key];
    if (!currentEntry) return current;
    return { ...current, [key]: { ...currentEntry, contextId } };
  });

  return { value, update, clear, flush, recoverForCurrentContext, dirty: Boolean(entry?.value.trim()), stale, storageFailed, targetId, serverConflict, serverReady, serverRevision };
}
