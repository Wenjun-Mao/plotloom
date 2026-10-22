import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
import { Button } from "../../components";
import type { DeletionFeedback } from "./useProjectDeletion";

export type PriorAbandonmentCandidate = Awaited<ReturnType<typeof plotloomApi.priorAbandonmentCandidates>>[number];

export function PriorProjectAbandonments({ refreshKey, disabled, onAbandon, feedback, commandProjectId, commandMessage }: {
  refreshKey: unknown; disabled: boolean; onAbandon?: (candidate: PriorAbandonmentCandidate) => Promise<void>;
  feedback?: DeletionFeedback; commandProjectId?: string; commandMessage?: string;
}) {
  const [items, setItems] = useState<PriorAbandonmentCandidate[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    void plotloomApi.priorAbandonmentCandidates().then(rows => { if (current) { setItems(rows); setError(""); } },
      reason => { if (current) { setItems([]); setError(String(reason instanceof Error ? reason.message : reason)); } });
    return () => { current = false; };
  }, [refreshKey]);
  return <>{error && <p role="alert">旧版项目删除入口读取失败：{error}。当前项目目录仍可使用。</p>}
    {items.length > 0 && <section aria-label="旧版项目放弃删除"><h3>旧版项目 · 仅可核对放弃删除</h3>
      <p>这些项目尚未升级，不能在当前版本打开或继续。列出项目不代表任务已结束，也不会修改素材。</p>
      {items.map(item => <article key={item.projectId} data-prior-project-id={item.projectId}>
        <strong>{item.title || "未命名项目"}</strong><p>项目 r{item.projectRevision} · 生命周期 r{item.lifecycleRevision}</p>
        <Button variant="danger" disabled={disabled || !onAbandon} onClick={() => void onAbandon?.(item)}>核对放弃删除「{item.title}」</Button>
        {commandProjectId === item.projectId && commandMessage && <p role="status">{commandMessage}</p>}
        {feedback?.id === item.projectId && <p role={feedback.error ? "alert" : "status"}>{feedback.message}</p>}
      </article>)}
    </section>}</>;
}
