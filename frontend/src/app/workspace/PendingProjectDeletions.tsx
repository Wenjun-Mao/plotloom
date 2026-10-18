import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
import { Button } from "../../components";

export type PendingProjectDeletion = Awaited<ReturnType<typeof plotloomApi.pendingProjectDeletions>>[number];

export function PendingProjectDeletions({ refreshKey, disabled, onRetry }: {
  refreshKey: unknown; disabled: boolean; onRetry?: (pending: PendingProjectDeletion) => Promise<void>;
}) {
  const [pending, setPending] = useState<PendingProjectDeletion[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    void plotloomApi.pendingProjectDeletions().then(rows => { if (current) { setPending(rows); setError(""); } },
      reason => { if (current) setError(String(reason instanceof Error ? reason.message : reason)); });
    return () => { current = false; };
  }, [refreshKey]);
  return <>{error && <p role="alert">待完成删除读取失败：{error}</p>}
    {pending.length > 0 && <section aria-label="待完成项目删除"><h3>待完成删除</h3>
      <p>已保存删除请求；观察此列表不会继续删除，也不会恢复派发。</p>
      {pending.map(item => <div key={item.projectId}><strong>{item.confirmationTitle}</strong>
        <p>{item.revoked ? "主机派发和发布权限已撤销，项目文件尚未确认全部删除。" : "主机撤销结果尚未确认，项目仍保留。"}</p>
        <Button variant="danger" disabled={disabled || !onRetry} onClick={() => void onRetry?.(item)}>{item.revoked ? "重试删除" : "重新核对并删除"}「{item.confirmationTitle}」</Button></div>)}
    </section>}</>;
}
