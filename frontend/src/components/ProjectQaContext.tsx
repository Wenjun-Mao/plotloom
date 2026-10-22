import { useEffect, useState } from "react";
import { ApiTransport } from "../api-transport";
import { browserProjectReads } from "../project-read-admission";

export type QaActor = { kind: "agent_operated_qa"; scopeId: string };
export type QaContext = { eligible: boolean; attribution: QaActor | null; required?: boolean; reason?: string | null };
const transport = new ApiTransport(globalThis.fetch, "/api/v2", browserProjectReads);
export const projectQaApi = { current: async (id: string, signal?: AbortSignal) =>
  (await transport.json<QaContext>(`/projects/${encodeURIComponent(id)}/qa-context`, { signal })).body };

export function useProjectQa(projectId?: string) {
  const [context, setContext] = useState<{ project: string; value: QaContext } | null>(null);
  const [enabled, setEnabled] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setContext(null); setEnabled(null); setFailed(false);
    if (!projectId) return;
    const abort = new AbortController();
    projectQaApi.current(projectId, abort.signal)
      .then(value => { if (!abort.signal.aborted) setContext({ project: projectId, value }); })
      .catch(() => { if (!abort.signal.aborted) setFailed(true); });
    return () => abort.abort();
  }, [projectId]);
  const value = context && context.project === projectId ? context.value : null;
  return { eligible: !!value?.eligible, required: !!value?.required, reason: value?.reason, ready: !!value, failed,
    enabled: enabled === projectId, setEnabled: (next: boolean) => setEnabled(next ? projectId || null : null),
    actor: enabled === projectId && value?.eligible ? value.attribution : null,
    blocked: !value || (value.required || value.eligible) && (!value.eligible || enabled !== projectId) };
}

export function ProjectQaContext({ qa }: { qa: ReturnType<typeof useProjectQa> }) {
  if (qa.failed) return <p role="alert">审阅身份待核实；请重新打开项目以读取授权，不会改为创作者确认。</p>;
  if (qa.required && !qa.eligible) return <p role="alert">{qa.reason || "此项目需要代理 QA 授权，当前不可用；不能改为创作者确认。"}</p>;
  if (!qa.eligible) return null;
  return <label><input type="checkbox" checked={qa.enabled} onChange={event => qa.setEnabled(event.target.checked)} />
    明确使用代理 QA 审阅（经用户授权，仅限当前一次性测试项目）</label>;
}
