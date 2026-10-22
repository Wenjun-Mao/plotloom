import type { AutopilotActivity, AutopilotRun } from "./contracts";
import { projectAutopilotProgress } from "./progress";

const owners: Record<string, string> = {
  outline: "故事大纲", branches: "故事路线", characters: "角色设定", art: "美术方向",
  script: "完整剧本", storyboard: "分镜", "bridge-intent": "戏剧意图",
  "bridge-presentation": "画面呈现", "character-reference": "角色参考",
  "art-reference": "美术参考", image: "镜头首帧",
};
const states: Record<AutopilotActivity["state"], string> = {
  waiting: "等待", queued: "排队", generating: "正在生成", validating: "正在校验",
  unknown: "结果待核对", cancelling: "正在结束原任务", delivered: "候选已保留",
  adopted: "AI 已采用", failed: "需要处理",
};

export function activityLabel(activity: AutopilotActivity, run: AutopilotRun) {
  if (activity.state === "failed" && activity.domain === "text") {
    const ordinal = Number(activity.operationKey.split(":").at(-1)) || 0;
    const later = run.checkpoints.filter(item => item.evidence.owner === activity.owner
      && item.operationKey.startsWith(`${activity.owner}:correction:`) && Number(item.operationKey.split(":").at(-1)) > ordinal);
    if (later.length) return later.some(item => item.state === "adopted") ? "失败记录已保留 · 后续修正已采用" : "失败记录已保留 · 已有后续修正";
  }
  const label = ["waiting", "queued"].includes(activity.state) && run.state === "paused"
    ? "已暂停，保留原任务" : states[activity.state];
  const corrective = activity.domain === "text" && ["outline", "characters", "art"].includes(activity.owner)
    && activity.operationKey.startsWith(`${activity.owner}:correction:`);
  return corrective ? `${label} · 修正第 ${activity.operationKey.split(":").at(-1)} 次` : label;
}

export function ConcurrentActivity({ run }: { run: AutopilotRun }) {
  const progress = projectAutopilotProgress(run);
  if (!progress.activities.length) return null;
  return <section className="autopilot-concurrent" aria-label="当前素材任务">
    <ul>{progress.activities.map(activity => <li key={activity.operationKey}>
      <span>{activity.domain === "image" ? "图片" : "文字"} · {owners[activity.owner] || "素材任务"}
        {activity.domain === "image" && ` · ${activity.subjectId}`}</span>
      <strong>{activityLabel(activity, run)}</strong>
    </li>)}</ul>
    {progress.activities.some(activity => activity.state === "unknown") && <p>原任务结果正在核对，请勿重复发送。</p>}
  </section>;
}
