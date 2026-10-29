import { ManualExecutionRetry, exhaustedExecution, type FailedExecution } from "../generation-retry/ManualExecutionRetry";
import type { AutopilotRun } from "./contracts";
const labels: Record<string, string> = { outline: "故事大纲", branches: "故事路线", characters: "角色设定", art: "美术方向", script: "剧本", storyboard: "分镜", "bridge-intent": "戏剧意图", "bridge-presentation": "画面呈现", image: "首帧图片", "character-reference": "角色参考图片", "art-reference": "美术参考图片" };
export function ExecutionRetries({ projectId, run, disabled, onRetry, onObserve }: {
  projectId: string; run: AutopilotRun; disabled: boolean;
  onRetry: (body: FailedExecution & { commandId: string }) => Promise<void>; onObserve: () => Promise<void>;
}) {
  if (["cancelled", "stale", "taken_over", "handed_off"].includes(run.state)) return null;
  const superseded = new Set(run.checkpoints.flatMap(checkpoint => checkpoint.retry?.predecessorJobIds || []));
  const current = run.checkpoints.filter(checkpoint => exhaustedExecution(checkpoint.retry) && !superseded.has(checkpoint.retry!.currentJobId!));
  if (!["running", "waiting"].includes(run.state)) return current.length ? <p>请先继续原运行，再决定是否手动重试当前失败任务。</p> : null;
  return <>{current.map(checkpoint =>
    <section key={checkpoint.operationKey} aria-label={`${labels[checkpoint.evidence.owner] || "素材"}执行失败重试`}>
      <p>{labels[checkpoint.evidence.owner] || "素材"}：执行重试已结束；内容拒绝仍须按内容问题处理。</p>
      <ManualExecutionRetry identity={`${projectId}:${run.id}:${run.revision}:${checkpoint.operationKey}`} status={checkpoint.retry} disabled={disabled} onRetry={onRetry} onObserve={onObserve} />
    </section>)}</>;
}
