import { useId } from "react";
import { creativeWorkflowStepReference } from "../../creative-workflow-steps";

export function FootageRequirementControl({ kind, footageMode, disabled, onChange }: {
  kind: "decision" | "join";
  footageMode: "footage" | "route_only";
  disabled: boolean;
  onChange: (enabled: boolean) => void;
}) {
  const descriptionId = useId();
  return <>
    <label className="footage-requirement-control">
      <input type="checkbox" aria-describedby={descriptionId} disabled={disabled} checked={footageMode === "footage"} onChange={event => onChange(event.target.checked)} />
      此节点需要拍摄
    </label>
    <div id={descriptionId} className="graph-node-footage-help">
      <p>勾选后需制作剧本场景、分镜和影片，时长计入完整路线。{kind === "decision" ? "先播放本节点影片，再显示问题与选项。" : "播放本节点影片后，再继续后续路线。"}不勾选则仅控制路线，无需拍摄。</p>
      <p>影响{creativeWorkflowStepReference("production")}：可能需要重新分配路线时长，并修订或重新审阅已有剧本、分镜和制作内容。目标时长不会自动增加；完成后在{creativeWorkflowStepReference("play")}核对受影响路线。此修改只更新当前图草稿；确认并应用后才影响故事路线，不会自动生成影片。</p>
    </div>
  </>;
}
