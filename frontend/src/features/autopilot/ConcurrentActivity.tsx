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
  const label = ["waiting", "queued"].includes(activity.state) && run.state === "paused"
    ? "已暂停，保留原任务" : states[activity.state];
  const corrective = activity.domain === "text" && ["outline", "characters", "art"].includes(activity.owner)
    && activity.operationKey === `${activity.owner}:correction:1`;
  return corrective ? `${label} · 自动修正 1/1` : label;
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
