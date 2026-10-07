import { Badge, Button, Panel } from "../../components";
import type { ShotRemovalImpact, ShotSceneMigrationImpact } from "../../storyboard-editor";

export function GateStatusBadge({ status }: { status: "pass" | "fail" | "skipped" | "not_applicable" }) {
  const tone = status === "pass" ? "ok" : status === "fail" ? "danger" : "warning";
  return <Badge tone={tone}>{status.toUpperCase()}</Badge>;
}

export function ShotMigrationConfirmation({ impact, onCancel, onConfirm }: { impact: ShotSceneMigrationImpact; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice warning" data-testid="shot-scene-migration-impact"><strong>镜头关系迁移确认</strong><p>将 Shot {impact.shotId} 从 {impact.fromSceneId} 迁移到 {impact.toSceneId}。Shot ID 不变，两个场景的镜头顺序会确定性归一化。</p><small>不会自动删除或迁移关联关系。迁移后跨场景的 cue 调度：{impact.crossSceneCueIds.join(", ") || "无"}；ShotBeatLink：{impact.crossSceneLinkKeys.join(", ") || "无"}。请在确认后显式调整这些关系。</small><div className="page-actions"><Button type="button" variant="primary" onClick={onConfirm}>确认迁移</Button><Button type="button" onClick={onCancel}>取消</Button></div></Panel>;
}

export function ShotDeletionConfirmation({ impact, title, onCancel, onConfirm }: { impact: ShotRemovalImpact; title: string; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice error" data-testid="shot-deletion-impact" role="alertdialog" aria-label="镜头删除影响确认">
    <strong>删除镜头“{title}”</strong>
    <p>镜头 {impact.shotId} 将被删除；同场景镜头顺序会重新编号。以下关系不会被隐藏处理：</p>
    <ul>
      {impact.linkBeatIds.map((beatId) => <li key={`link:${beatId}`}>删除 ShotBeatLink：{impact.shotId} → {beatId}</li>)}
      {impact.unscheduledCueIds.map((cueId) => <li key={`cue:${cueId}`}>DialogueCue 将变为未调度：{cueId}</li>)}
      {!impact.linkBeatIds.length && !impact.unscheduledCueIds.length && <li>没有 ShotBeatLink 或 DialogueCue 调度关系。</li>}
    </ul>
    <div className="page-actions"><Button type="button" variant="danger" data-testid="confirm-shot-delete" onClick={onConfirm}>确认删除</Button><Button type="button" onClick={onCancel}>取消</Button></div>
  </Panel>;
}
