import { RetainedDraftNotice } from "./RetainedDraftNotice";
import { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button, ErrorNotice } from "../../components";
import type { ReviewDraftStore, ReviewEditor } from "./reviewDraftStore";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";

export const ReviewDraftContext = createContext<{ store: ReviewDraftStore; quiescence: ProjectDraftQuiescence; projectId: string; revision: number; enabled: boolean } | null>(null);
const noSubscribe = () => () => undefined;
const noSnapshot = () => 0;

/** Explicit review/dispatch inputs cannot be implicitly accepted by Close. */
export function useExplicitReviewCloseGuard(projectId: string, editorId: string, dirty: boolean, busy: boolean, discardLocal: () => void, label: string, retainedFile: File | null = null) {
  const context = useContext(ReviewDraftContext);
  const binding = `${projectId}:${editorId}`;
  const current = useRef({ binding, dirty, busy, discardLocal, label, retainedFile, mounted: true });
  if (current.current.binding !== binding) current.current = { binding, dirty, busy, discardLocal, label, retainedFile, mounted: true };
  else Object.assign(current.current, { dirty, busy, discardLocal, label, retainedFile });
  useEffect(() => {
    if (!context?.enabled || context.projectId !== projectId) return;
    const owner = current.current;
    owner.mounted = true;
    const unregister = context.quiescence.register(projectId, `explicit_review:${editorId}`, async () => {
      if (owner.dirty || owner.busy) throw new Error(`${owner.label}尚有未导入文件或操作未完成；请先完成、复制或明确丢弃该输入。`);
      return true;
    }, {
      pending: () => owner.dirty, locallyPreserved: () => !owner.dirty,
      preserveForDeparture: () => !owner.dirty, retainOnUnmount: dirty,
      discardUnsent: async () => {
        owner.dirty = false; owner.retainedFile = null;
        if (owner.mounted && current.current === owner) owner.discardLocal();
        else owner.busy = false;
      },
    });
    return () => { owner.mounted = false; unregister(); };
  }, [context?.enabled, context?.quiescence, context?.projectId, projectId, editorId, dirty, busy]);
}

/** Recovery is explicit; a stale buffer is inspectable, never silently rebased. */
export function useReviewEditorDraft(projectId: string, editor: ReviewEditor, basis: string, onRestore: (text: string) => void, disabled = false, onDiscard?: () => void, targetId = "", independentBaseRevision?: number) {
  const context = useContext(ReviewDraftContext);
  const baseRevision = independentBaseRevision ?? context?.revision ?? 0;
  const [error, setError] = useState("");
  const binding = `${projectId}:${editor}:${targetId}:${basis}:${baseRevision}`;
  const activeOwner = useRef({ binding });
  if (activeOwner.current.binding !== binding) activeOwner.current = { binding };
  const owner = activeOwner.current;
  useEffect(() => setError(""), [binding]);
  const store = context?.enabled && context.projectId === projectId ? context.store : undefined;
  const version = useSyncExternalStore(store?.subscribe ?? noSubscribe, store?.snapshot ?? noSnapshot);
  const entry = store?.get(projectId, editor, targetId);
  const authoredHere = useRef<{ binding: string; text: string } | undefined>(undefined);
  if (!entry) authoredHere.current = undefined;
  const rejected = store?.rejected(projectId, editor, targetId);
  const retained = store?.retained(projectId, editor, targetId) ?? [];
  const current = Boolean(entry && entry.payload.basis === basis && entry.baseRevision === baseRevision && !entry.conflict);
  useEffect(() => {
    if (!entry?.editing || !current || authoredHere.current?.binding === binding && authoredHere.current.text === entry.payload.text) return;
    try { onRestore(entry.payload.text); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "草稿无法填回，请复制内容。"); }
    // Only the store's explicit restore/update event may apply the buffer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store, projectId, editor, entry?.localRevision, entry?.editing, current, targetId]);
  const clear = async () => {
    try {
      await store?.clear(projectId, editor, targetId, entry ?? null);
      if (activeOwner.current !== owner) return false;
      setError(""); return true;
    } catch {
      if (activeOwner.current === owner) setError("保留草稿未能丢弃；内容仍受保护，请重试。");
      return false;
    }
  };
  const notice = entry && (!entry.editing || !current || error || entry.failed) ? <div className="notice warning" role="status">
    <strong>{entry.ownershipConflict ? "保留输入属于另一个浏览器会话" : current ? "已在本机保留，尚未同步" : "保留草稿的版本已变化"}</strong>
    <span>{current ? "恢复只填回编辑器，不会确认内容或启动生成。" : "可复制或丢弃；不会自动套用到当前版本。"}</span>
    <div className="button-row"><Button variant="quiet" disabled={disabled} onClick={() => void clear().then(cleared => { if (cleared && activeOwner.current === owner) onDiscard?.(); })}>丢弃保留草稿</Button>
      <Button variant="quiet" onClick={() => void navigator.clipboard.writeText(entry.payload.text)}>复制草稿内容</Button>
</div>
    {!current && <details><summary>查看保留内容</summary><pre>{entry.payload.text}</pre></details>}
  </div> : null;
  return {
    changed(text: string) {
      if (!store || !basis || disabled) return false;
      const accepted = store.update(projectId, editor, baseRevision, basis, text, targetId);
      if (accepted) authoredHere.current = { binding, text };
      else setError("当前输入的来源已变化，尚未保留；请复制内容，或明确丢弃后再离开。");
      return accepted;
    },
    clear, notice: <>{rejected && <div role="alert"><p>当前来源变化后的输入尚未保留；离开已暂停。</p><pre>{rejected.text}</pre><Button onClick={() => void navigator.clipboard.writeText(rejected.text)}>复制当前未保留输入</Button></div>}{notice}<RetainedDraftNotice entries={retained} onDiscard={entry => store?.discardRetained(entry)} onResume={disabled ? undefined : entry => store?.resumeRetained(projectId, editor, targetId, basis, baseRevision, entry)} />{error && <ErrorNotice message={error} />}{store?.storageFailed() && <ErrorNotice message="本标签页草稿暂存失败；关闭前请保存或复制内容。" />}</>,
    version, stale: Boolean(entry && !current || !entry && retained.length),
    preserved: !store?.storageFailed(),
    pending: Boolean(entry?.failed),
  };
}
