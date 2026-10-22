import { useAutopilot, useAdoptionLabel } from "./AutopilotWorkspace";
import type { AutopilotRun } from "./contracts";

const phases: Record<string, string> = { source: "故事来源", outline: "故事大纲", branches: "剧情分支", characters: "角色设定", art: "美术设定", script: "完整剧本", storyboard: "分镜", "bridge-intent": "戏剧意图", "bridge-presentation": "画面呈现", references: "参考图片", "first-frames": "镜头首帧", "material-review": "完整素材审阅", "manual-video": "手动视频制作" };

export function automaticGuidance(run: AutopilotRun | null, ready: boolean): string | null {
  if (!ready) return "自动素材状态与采用来源尚待核实；请先恢复状态读取。阅读报告不会确认或修改内容。";
  if (!run || ["cancelled", "taken_over", "stale", "handed_off"].includes(run.state)) return null;
  const phase = phases[run.phase] || "制作规划";
  const activity = run.state === "paused" ? "自动素材已暂停"
    : run.state === "blocked" ? "自动素材需要处理，请查看上方运行状态"
    : run.state === "awaiting_review" ? "完整素材已准备，等待你在上方一次审阅"
    : "AI 正在自动准备素材，无需手动准备或发送当前任务";
  return `${activity}。当前自动阶段：${phase}。全部路线和图片准备完成后，仍需一次完整人工审阅。你可以继续阅读或手动编辑；保存手动修改将接管自动运行。阅读报告不会确认、接管或发送任务。`;
}

export function useKnownAutomaticRun() {
  const owner = useAutopilot();
  return !!owner?.ready && automaticGuidance(owner.run, true) !== null;
}

export function useAutomaticGuidance() {
  const owner = useAutopilot();
  return owner?.projectId ? automaticGuidance(owner.run, owner.ready) : null;
}

export function useBridgeAdoptionLabel() {
  const label = useAdoptionLabel();
  return (revision: number, hash: string) => {
    const presentation = label("bridge-presentation", revision, hash);
    const intent = label("bridge-intent", revision, hash);
    return presentation === "AI 已采用" || intent === "AI 已采用" ? "AI 已采用" : presentation;
  };
}
