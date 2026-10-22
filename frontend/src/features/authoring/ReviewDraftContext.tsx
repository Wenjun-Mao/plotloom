import { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button, ErrorNotice } from "../../components";
import type { ReviewDraftStore, ReviewEditor } from "./reviewDraftStore";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";

export const ReviewDraftContext = createContext<{ store: ReviewDraftStore; quiescence: ProjectDraftQuiescence; projectId: string; revision: number; enabled: boolean } | null>(null);
const noSubscribe = () => () => undefined;
const noSnapshot = () => 0;

/** Explicit review/dispatch inputs cannot be implicitly accepted by Close. */
export function useExplicitReviewCloseGuard(projectId: string, editorId: string, dirty: boolean, busy: boolean, discardLocal: () => void, label: string) {
  const context = useContext(ReviewDraftContext);
  const binding = `${projectId}:${editorId}`;
  const current = useRef({ binding, dirty, busy, discardLocal, label });
  if (current.current.binding !== binding) current.current = { binding, dirty, busy, discardLocal, label };
  else Object.assign(current.current, { dirty, busy, discardLocal, label });
  useEffect(() => {
    if (!context?.enabled || context.projectId !== projectId) return;
    const owner = current.current;
    return context.quiescence.register(projectId, `explicit_review:${editorId}`, async () => {
      if (owner.dirty || owner.busy) throw new Error(`${owner.label}尚有未保存修改或操作未完成；请先完成该操作，或确认丢弃未保存修改后强制关闭。`);
      return true;
    }, { retainOnUnmount: dirty || busy, discardUnsent: async () => { if (current.current === owner) owner.discardLocal(); } });
  }, [context?.enabled, context?.quiescence, context?.projectId, projectId, editorId, dirty, busy]);
}

/** Recovery is explicit; a stale buffer is inspectable, never silently rebased. */
export function useReviewEditorDraft(projectId: string, editor: ReviewEditor, basis: string, onRestore: (text: string) => void, disabled = false, onDiscard?: () => void) {
  const context = useContext(ReviewDraftContext);
  const [error, setError] = useState("");
  const binding = `${projectId}:${editor}:${basis}:${context?.revision ?? 0}`;
  const activeOwner = useRef({ binding });
  if (activeOwner.current.binding !== binding) activeOwner.current = { binding };
  const owner = activeOwner.current;
  useEffect(() => setError(""), [binding]);
  const store = context?.enabled && context.projectId === projectId ? context.store : undefined;
  const version = useSyncExternalStore(store?.subscribe ?? noSubscribe, store?.snapshot ?? noSnapshot);
  const entry = store?.get(projectId, editor);
  const current = Boolean(entry && entry.payload.basis === basis && entry.baseRevision === context?.revision);
  useEffect(() => {
    if (!entry?.editing || !current) return;
    try { onRestore(entry.payload.text); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "草稿无法填回，请复制内容。"); }
    // Only the store's explicit restore/update event may apply the buffer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store, projectId, editor, entry?.localRevision, entry?.editing, current]);
  const clear = async () => {
    try {
      await store?.clear(projectId, editor);
      if (activeOwner.current !== owner) return false;
      setError(""); return true;
    } catch {
      if (activeOwner.current === owner) setError("保留草稿未能丢弃；内容仍受保护，请重试。");
      return false;
    }
  };
  const notice = entry && (!entry.editing || !current || error) ? <div className="notice warning" role="status">
    <strong>{current ? "发现已保留的编辑草稿" : "保留草稿的版本已变化"}</strong>
    <span>{current ? "恢复只填回编辑器，不会确认内容或启动生成。" : "可复制或丢弃；不会自动套用到当前版本。"}</span>
    <div className="button-row"><Button variant="quiet" disabled={disabled} onClick={() => void clear().then(cleared => { if (cleared && activeOwner.current === owner) onDiscard?.(); })}>丢弃保留草稿</Button>
      <Button variant="quiet" onClick={() => void navigator.clipboard.writeText(entry.payload.text)}>复制草稿内容</Button>
      {current && <Button disabled={disabled} onClick={() => store?.restore(projectId, editor)}>恢复编辑草稿</Button>}</div>
    {!current && <details><summary>查看保留内容</summary><pre>{entry.payload.text}</pre></details>}
  </div> : null;
  return {
    changed(text: string) { if (store && basis && !disabled) store.update(projectId, editor, context!.revision, basis, text); },
    clear, notice: <>{notice}{error && <ErrorNotice message={error} />}{store?.storageFailed() && <ErrorNotice message="本标签页草稿暂存失败；关闭前请保存或复制内容。" />}</>,
    version, stale: Boolean(entry && !current),
  };
}
