import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";

export type IntentDraft = { identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string };
type Entry = { baseId: string | null; value: IntentDraft };
type Drafts = Record<string, Entry>;
const storageKey = "plotloom:visual-intent-drafts:v1";
const imageJobStorageKey = "plotloom:image-job-direction-drafts:v1";
const fields = ["identityIntent", "compositionIntent", "styleIntent", "sourceRefs"] as const;

function readDrafts(): Drafts {
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(storageKey) ?? "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry
      && (entry.baseId === null || typeof entry.baseId === "string")
      && entry.value && fields.every((field) => typeof entry.value[field] === "string")));
  } catch { return {}; }
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
) {
  const [drafts, setDrafts] = useState<Drafts>(readDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const [serverRevision, setServerRevision] = useState(0);
  const serverRevisionRef = useRef(0);
  const acknowledgedPayloadRef = useRef<string | undefined>(undefined);
  const persistenceRef = useRef<Promise<void> | undefined>(undefined);
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
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !assetId || !baseCanonicalRevision || !entry || !serverReady || serverConflict) return;
    const timer = window.setTimeout(() => {
      const epoch = requestEpochRef.current;
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
      if (!payload.sourceRefs.length || acknowledgedPayloadRef.current === fingerprint) return;
      const persistence = plotloomApi.saveAuthoringDraft(projectId, {
        editorScope: "visual_intent",
        entityId,
        baseCanonicalRevision,
        expectedDraftRevision: serverRevisionRef.current,
        payload,
      }).then((receipt) => {
        if (requestEpochRef.current !== epoch) return;
        serverRevisionRef.current = receipt.draftRevision;
        acknowledgedPayloadRef.current = fingerprint;
        setServerRevision(receipt.draftRevision);
        serverConflictRef.current = false;
        setServerConflict(false);
      }).catch(() => {
        if (requestEpochRef.current !== epoch) return;
        serverConflictRef.current = true;
        setServerConflict(true);
      });
      persistenceRef.current = persistence;
      void persistence.finally(() => {
        if (persistenceRef.current === persistence) persistenceRef.current = undefined;
      });
    }, 750);
    return () => window.clearTimeout(timer);
  }, [assetId, baseCanonicalRevision, entityId, entry, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId]);
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
  return { value, update, clear, dirty, stale, storageFailed, serverConflict, serverReady, serverRevision };
}

export type ImageJobDraftTarget =
  | { kind: "original" }
  | { kind: "refinement"; parentCandidateAssetId: string }
  | { kind: "keyframe_adaptation"; profileId: string; profileLabel: string };

type ImageJobDraftEntry = { contextId: string; value: string };
type ImageJobDrafts = Record<string, ImageJobDraftEntry>;

function readImageJobDrafts(): ImageJobDrafts {
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(imageJobStorageKey) ?? "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry
      && typeof entry.contextId === "string" && typeof entry.value === "string"));
  } catch { return {}; }
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
) {
  const [drafts, setDrafts] = useState<ImageJobDrafts>(readImageJobDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const [serverRevision, setServerRevision] = useState(0);
  const serverRevisionRef = useRef(0);
  const acknowledgedPayloadRef = useRef<string | undefined>(undefined);
  const persistenceRef = useRef<Promise<void> | undefined>(undefined);
  const [serverReady, setServerReady] = useState(false);
  const [serverConflict, setServerConflict] = useState(false);
  const serverConflictRef = useRef(false);
  const requestEpochRef = useRef(0);
  const targetId = target.kind === "original"
    ? "original"
    : target.kind === "refinement"
      ? `refinement:${target.parentCandidateAssetId}`
      : `keyframe_adaptation:${target.profileId}`;
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
  useEffect(() => {
    if (!serverDraftsEnabled || !projectId || !shotId || !baseCanonicalRevision || !entry?.value.trim() || !serverReady || serverConflict) return;
    const timer = window.setTimeout(() => {
      const epoch = requestEpochRef.current;
      const payload = { shotId, targetId, contextId: entry.contextId, presentationChange: entry.value };
      const fingerprint = JSON.stringify(payload);
      if (acknowledgedPayloadRef.current === fingerprint) return;
      const persistence = plotloomApi.saveAuthoringDraft(projectId, {
        editorScope: "image_direction", entityId, baseCanonicalRevision,
        expectedDraftRevision: serverRevisionRef.current,
        payload,
      }).then((receipt) => {
        if (requestEpochRef.current !== epoch) return;
        serverRevisionRef.current = receipt.draftRevision;
        acknowledgedPayloadRef.current = fingerprint;
        setServerRevision(receipt.draftRevision);
        serverConflictRef.current = false;
        setServerConflict(false);
      }).catch(() => {
        if (requestEpochRef.current !== epoch) return;
        serverConflictRef.current = true;
        setServerConflict(true);
      });
      persistenceRef.current = persistence;
      void persistence.finally(() => {
        if (persistenceRef.current === persistence) persistenceRef.current = undefined;
      });
    }, 750);
    return () => window.clearTimeout(timer);
  }, [baseCanonicalRevision, contextId, entityId, entry, projectId, serverConflict, serverDraftsEnabled, serverReady, shotId, targetId]);
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

  return { value, update, clear, recoverForCurrentContext, dirty: Boolean(entry?.value.trim()), stale, storageFailed, targetId, serverConflict, serverReady, serverRevision };
}
