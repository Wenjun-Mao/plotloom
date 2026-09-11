import { useEffect, useState } from "react";

export type IntentDraft = { identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string };
type Entry = { baseId: string | null; value: IntentDraft };
type Drafts = Record<string, Entry>;
const storageKey = "plotloom:visual-intent-drafts:v1";
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
