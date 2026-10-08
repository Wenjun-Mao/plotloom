import { Badge, Button, Panel } from "../../components";
import type { ShotRemovalImpact, ShotSceneMigrationImpact } from "../../storyboard-editor";

export function GateStatusBadge({ status }: { status: "pass" | "fail" | "skipped" | "not_applicable" }) {
  const tone = status === "pass" ? "ok" : status === "fail" ? "danger" : "warning";
  return <Badge tone={tone}>{{ pass: "通过", fail: "未通过", skipped: "已跳过", not_applicable: "不适用" }[status]}</Badge>;
}

export function ShotMigrationConfirmation({ impact, onCancel, onConfirm }: { impact: ShotSceneMigrationImpact; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice warning" data-testid="shot-scene-migration-impact"><strong>镜头所属场景变更</strong><p>将镜头 {impact.shotId} 从场景 {impact.fromSceneId} 移到场景 {impact.toSceneId}。镜头标识不变，两个场景的镜头顺序会重新编号。</p><small>相关对白和节拍覆盖需要单独调整。移动后跨场景的对白安排：{impact.crossSceneCueIds.join(", ") || "无"}；节拍覆盖关系：{impact.crossSceneLinkKeys.join(", ") || "无"}。请在确认后调整这些关系。</small><div className="page-actions"><Button type="button" variant="primary" onClick={onConfirm}>确认迁移</Button><Button type="button" onClick={onCancel}>取消</Button></div></Panel>;
}

export function ShotDeletionConfirmation({ impact, title, onCancel, onConfirm }: { impact: ShotRemovalImpact; title: string; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice error" data-testid="shot-deletion-impact" role="alertdialog" aria-label="镜头删除影响确认">
    <strong>删除镜头“{title}”</strong>
    <p>镜头 {impact.shotId} 将被删除；同场景镜头顺序会重新编号。同时会调整以下关系：</p>
    <ul>
      {impact.linkBeatIds.map((beatId) => <li key={`link:${beatId}`}>删除节拍覆盖关系：{impact.shotId} → {beatId}</li>)}
      {impact.unscheduledCueIds.map((cueId) => <li key={`cue:${cueId}`}>对白将不再安排到此镜头：{cueId}</li>)}
      {!impact.linkBeatIds.length && !impact.unscheduledCueIds.length && <li>没有节拍覆盖或对白安排。</li>}
    </ul>
    <div className="page-actions"><Button type="button" variant="danger" data-testid="confirm-shot-delete" onClick={onConfirm}>确认删除</Button><Button type="button" onClick={onCancel}>取消</Button></div>
  </Panel>;
}
