import { useEffect, useState } from "react";

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
export function useVisualIntentDraft(projectId: string | undefined, shotId: string | undefined, assetId: string, baseId: string | undefined, saved: IntentDraft) {
  const [drafts, setDrafts] = useState<Drafts>(readDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const key = JSON.stringify([projectId, shotId, assetId]);
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
  useEffect(() => {
    if (!Object.keys(drafts).length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [drafts]);

  const clear = () => setDrafts((current) => {
    const next = { ...current };
    delete next[key];
    return next;
  });
  const update = (change: (current: IntentDraft) => IntentDraft) => {
    if (!projectId || !shotId || !assetId) return;
    setDrafts((current) => ({ ...current, [key]: {
      baseId: current[key] ? current[key].baseId : baseId ?? null,
      value: change(current[key]?.value ?? saved),
    } }));
  };
  return { value, update, clear, dirty, stale, storageFailed };
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
) {
  const [drafts, setDrafts] = useState<ImageJobDrafts>(readImageJobDrafts);
  const [storageFailed, setStorageFailed] = useState(false);
  const targetId = target.kind === "original"
    ? "original"
    : target.kind === "refinement"
      ? `refinement:${target.parentCandidateAssetId}`
      : `keyframe_adaptation:${target.profileId}`;
  const key = JSON.stringify([projectId, shotId, targetId]);
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
  const clear = () => setDrafts((current) => {
    const next = { ...current };
    delete next[key];
    return next;
  });
  // Recovery is deliberate: it retains the text but rebases it only after the
  // creator has seen that its Approval, storyboard, or reviewed target changed.
  const recoverForCurrentContext = () => setDrafts((current) => {
    const currentEntry = current[key];
    if (!currentEntry) return current;
    return { ...current, [key]: { ...currentEntry, contextId } };
  });

  return { value, update, clear, recoverForCurrentContext, dirty: Boolean(entry?.value.trim()), stale, storageFailed, targetId };
}
