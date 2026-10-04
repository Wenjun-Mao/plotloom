/** Tab-local erasure by project identity, independent of mounted writers. */
import { useEffect, type Dispatch, type SetStateAction } from "react";

type Erasure = { projectId: string } | { storageKey: string; entryKey: string };
const consumers = new Set<(event: Erasure) => void>();
const mediaKeys = ["plotloom:visual-intent-drafts:v1", "plotloom:image-job-direction-drafts:v1"];

function mediaProject(entryKey: string): string | undefined {
  try { const key: unknown = JSON.parse(entryKey); return Array.isArray(key) && typeof key[0] === "string" ? key[0] : undefined; }
  catch { return undefined; }
}

function removeEntries(storageKey: string, matches: (entryKey: string) => boolean) {
  const raw = window.sessionStorage.getItem(storageKey);
  if (!raw) return;
  const entries: unknown = JSON.parse(raw);
  if (!entries || typeof entries !== "object" || Array.isArray(entries)) throw new Error("项目草稿缓存格式无法确认");
  const retained = Object.fromEntries(Object.entries(entries).filter(([key]) => !matches(key)));
  window.sessionStorage.setItem(storageKey, JSON.stringify(retained));
}

/** A retained writer must also invalidate other editors' whole-cache snapshots. */
export function discardMediaDraftEntry(storageKey: string, entryKey: string) {
  removeEntries(storageKey, key => key === entryKey);
  for (const consumer of consumers) consumer({ storageKey, entryKey });
}

export function useMediaDraftErasure<T>(storageKey: string, setEntries: Dispatch<SetStateAction<Record<string, T>>>) {
  useEffect(() => {
    const consume = (event: Erasure) => {
      if ("storageKey" in event && event.storageKey !== storageKey) return;
      setEntries(current => Object.fromEntries(Object.entries(current).filter(([key]) =>
        "projectId" in event ? mediaProject(key) !== event.projectId : key !== event.entryKey)));
    };
    consumers.add(consume);
    return () => { consumers.delete(consume); };
  }, [setEntries, storageKey]);
}

/** Call only after the server confirms erasure; never on failed admission. */
export function discardProjectDraftCaches(projectId: string) {
  const failures: unknown[] = [];
  const erase = (action: () => void) => { try { action(); } catch (error) { failures.push(error); } };
  for (const key of ["plotloom:workbench-drafts:v1", "plotloom:review-editor-drafts:v1"])
    erase(() => removeEntries(key, entry => entry.startsWith(`${projectId}:`)));
  for (const key of mediaKeys) erase(() => removeEntries(key, entry => mediaProject(entry) === projectId));
  const presentationKeys = Array.from({ length: window.sessionStorage.length }, (_, index) => window.sessionStorage.key(index))
    .filter((key): key is string => Boolean(key?.startsWith(`plotloom:shot-presentation:${projectId}:`)));
  for (const key of presentationKeys) erase(() => window.sessionStorage.removeItem(key));
  for (const consumer of consumers) consumer({ projectId });
  if (failures.length) throw new Error("项目已删除，但部分本地草稿缓存未能清除");
}
