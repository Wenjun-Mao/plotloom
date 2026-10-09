import { useState } from "react";
import { formatUiTimestamp } from "../../ui-time";
import { Badge, Button, ErrorNotice } from "../../components";
import { stageLabels } from "../../model";
import { canRequestRunCancellation, runCancellationLabel, runKindLabels, runStatusLabels, workUnitStatusLabels } from "../../run-presentation";
import type { PipelineRun, QuarantineItem, RunProgress, ServerStageName, StoryboardReview, WorkspaceProject } from "../../types";
type DraftRecoverySource = "server" | "session" | "reconcile";
function formatDuration(durationMs: number | null | undefined): string { return durationMs == null ? "—" : durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`; }

export function WorkspaceInspector({ currentLabel, project, routeEntity, stageOverview, run, progress, review, readOnly, frozenProfileId, frozenProfileNeedsKey, onAuthorizeProfile, onOpenTrace, onResume, onCancel, onRepair, onRebuild }: {
  currentLabel: string;
  project: WorkspaceProject;
  routeEntity: string;
  stageOverview: Array<{ stage: ServerStageName; status: string }>;
  run?: PipelineRun;
  progress?: RunProgress;
  review: StoryboardReview | null;
  readOnly: boolean;
  frozenProfileId: string;
  frozenProfileNeedsKey: boolean;
  onAuthorizeProfile: () => void;
  onOpenTrace: () => void;
  onResume: () => Promise<void>;
  onCancel: () => Promise<void>;
  onRepair: (item: QuarantineItem) => Promise<void>;
  onRebuild: (stage: ServerStageName) => void;
}) {
  const requiredGates = review?.gateEvaluation?.results.filter((gate) => gate.required) ?? [];
  const failedRequiredGates = requiredGates.filter((gate) => gate.status !== "pass");
  return <aside className="workspace-inspector" data-testid="workspace-inspector">
    <span className="eyebrow">当前详情</span><strong>{currentLabel}</strong>
    <dl><div><dt>项目版本</dt><dd>r{project.revision}</dd></div><div><dt>实体</dt><dd>{routeEntity || "未选择"}</dd></div></dl>
    <div className="inspector-stages"><span className="eyebrow">正式内容</span>{stageOverview.map(({ stage, status }) => {
      const stageProgress = progress?.stageProgress.find((candidate) => candidate.stage === stage);
      return <div key={stage}><span>{stageLabels[stage]}{stageProgress && <small>{stageProgress.completedUnitCount}/{stageProgress.unitCount} 个子任务 · {stageProgress.sealed ? "已封存" : "未封存"}</small>}</span><Badge tone={status === "ready" ? "ok" : status === "stale" ? "warning" : "neutral"}>{status === "ready" ? "可用" : status === "stale" ? "需更新" : status === "missing" ? "尚未生成" : status}</Badge></div>;
    })}</div>
    <div className="inspector-run"><span className="eyebrow">最新运行</span>{run ? <><strong>{runStatusLabels[run.status]} · {runKindLabels[run.kind]}</strong><small>{run.id}</small><small>{run.startedAt ? `开始 ${formatUiTimestamp(run.startedAt)}` : `创建 ${formatUiTimestamp(run.createdAt)}`}{run.finishedAt ? ` · 完成 ${formatUiTimestamp(run.finishedAt)}` : ""}</small>{progress?.failureCode && <small className="danger-copy">{progress.failureCode}</small>}{frozenProfileNeedsKey && <div className="notice warning"><strong>此任务缺少可用密钥</strong><span>请为此任务的模型配置补充当前标签页密钥，保存后返回“继续运行”。不会自动切换模型。配置标识：{frozenProfileId}。</span><Button variant="quiet" onClick={onAuthorizeProfile}>查看此任务的模型配置</Button></div>}<Button variant="quiet" onClick={onOpenTrace}>查看提示词与原始响应</Button></> : <small>尚无运行记录</small>}</div>
    {progress && <details className="inspector-units" open={progress.status === "quarantined"}><summary>子任务 · {progress.workUnits.length}</summary>{progress.workUnits.map((unit) => {
      const attempt = unit.latestAttempt;
      const quarantine = project.quarantines.find((item) => item.id === unit.workUnitId);
      return <div className="inspector-unit" key={unit.workUnitId}><strong>{stageLabels[unit.stage]} · #{unit.sequence}</strong><small>{workUnitStatusLabels[unit.status]} · {unit.sealed ? "已封存" : "未封存"}</small><small>执行次数 {attempt ? `${attempt.attemptNumber}/${unit.maxAttempts}` : `—/${unit.maxAttempts}`} · {formatDuration(attempt?.durationMs)} · 令牌用量 {attempt?.inputTokens ?? "—"}/{attempt?.outputTokens ?? "—"}</small>{attempt?.outcomeCode && <small>{attempt.outcomeCode}</small>}{unit.repairEligible && quarantine && <Button variant="quiet" disabled={readOnly} onClick={() => void onRepair(quarantine)}>单独修复此子任务</Button>}</div>;
    })}</details>}
    {progress && <div className="inspector-actions"><span className="eyebrow">当前可用操作</span>{progress.actions.canResume && <Button variant="quiet" disabled={readOnly} onClick={() => void onResume()}>继续运行</Button>}{progress.actions.canCancel && <Button variant="danger" disabled={readOnly || !canRequestRunCancellation(run)} onClick={() => void onCancel()}>{runCancellationLabel(run)}</Button>}{progress.actions.canRebuildStage && <Button variant="quiet" disabled={readOnly || !progress.failedStage} onClick={() => progress.failedStage && onRebuild(progress.failedStage)}>从失败阶段完整重建</Button>}</div>}
    <div className="inspector-review"><span className="eyebrow">校验与批准</span>{review?.gateEvaluation ? <><strong>{failedRequiredGates.length ? `${failedRequiredGates.length} 个必需校验项未通过` : `${requiredGates.length} 个必需校验项已通过`}</strong><small>{review.gateEvaluation.gateSetVersion}</small></> : <small>尚无校验记录</small>}{review?.activeApproval ? <><Badge tone="ok">已批准</Badge><small>{review.activeApproval.reviewer} · r{review.activeApproval.subjectRevision}</small></> : <Badge tone={failedRequiredGates.length ? "danger" : "neutral"}>未批准</Badge>}</div>
    {readOnly && <p>归档项目不可编辑或运行。请在项目目录中恢复后继续。</p>}
  </aside>;
}

export { SettingsDialog } from "./SettingsDialog";

export function RebuildDialog({ staleStages, busy, onClose, onRebuild }: { staleStages: ServerStageName[]; busy: boolean; onClose: () => void; onRebuild: (stage: ServerStageName) => Promise<void> }) {
  const [stage, setStage] = useState<ServerStageName>(staleStages[0] || "story_bible");
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rebuild-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card compact"><header><div><span>Dependency-aware rebuild</span><h2 id="rebuild-title">重建过期阶段</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice warning"><strong>现有内容不会静默覆盖</strong><span>服务器从选择的阶段创建可追踪运行；验证失败的输出进入隔离区。</span></div><label><span>从哪个阶段开始</span><select value={stage} onChange={(event) => setStage(event.target.value as ServerStageName)}>{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((item) => <option key={item} value={item}>{stageLabels[item]}{staleStages.includes(item) ? " · 待重建" : ""}</option>)}</select></label></div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button variant="primary" disabled={busy} onClick={() => void onRebuild(stage)}>创建重建运行</Button></footer></section></div>;
}

export function WelcomeOnboarding({ onBlank, onSample, onDirectory }: { onBlank: () => void; onSample: () => void; onDirectory: () => void }) {
  return <main className="welcome-shell"><section className="welcome-card"><div className="brand-mark">PL</div><span className="eyebrow">Plotloom 创作工作台</span><h1>从一个项目开始</h1><p>创建空白项目以编写自己的故事，打开示例以浏览完整工作流，或从目录继续已有项目。</p><div className="welcome-actions"><Button variant="primary" onClick={onBlank}>创建空白项目</Button><Button onClick={onSample}>打开示例项目</Button><Button variant="quiet" onClick={onDirectory}>打开项目目录</Button></div><small>示例不会在未选择时自动加载，也不会覆盖加载失败的项目。</small></section></main>;
}

export { ProjectDirectoryDialog } from "./ProjectDirectoryDialog";

export { DraftNavigationDialog } from "./DraftNavigationDialog";

export function DraftRecoveryDialog({ source, autoSaveAvailable, busy = false, onRestore, onDiscard }: { busy?: boolean; source: DraftRecoverySource; autoSaveAvailable: boolean; onRestore: () => void; onDiscard: () => void }) {
  const detail = source === "server"
    ? "此草稿已保存在项目中；恢复后可继续修改。"
    : source === "reconcile"
      ? autoSaveAvailable
        ? "当前标签页与项目中各有一份草稿。恢复后会自动保存本标签页的输入，替换项目中这份草稿；已确认内容保持不变。"
        : "当前标签页与项目中各有一份草稿。恢复只会将本标签页的输入带回编辑器；请手动保存。"
      : autoSaveAvailable
        ? "此草稿只保留在当前标签页。恢复后会自动保存到项目中，不会修改已确认内容。"
        : "此草稿只保留在当前标签页。恢复后可继续编辑；请手动保存到项目。";
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-recovery-title"><button className="modal-backdrop" aria-label="保留提示" /><section className="modal-card compact"><header><div><span>{source === "server" ? "项目中的草稿" : "恢复当前标签页草稿"}</span><h2 id="draft-recovery-title">发现可恢复草稿</h2></div></header><div className="modal-body"><div className="notice"><strong>正式内容保持不变</strong><span>{detail}</span></div></div><footer><Button variant="quiet" disabled={busy} onClick={onDiscard}>丢弃草稿</Button><Button variant="primary" disabled={busy} onClick={onRestore}>{busy ? "正在核实…" : "恢复草稿"}</Button></footer></section></div>;
}

export function DraftConflictDialog({ serverReloaded, reloading, busy, graphRecovery = false, onReload, onCopy, onDiscard }: { serverReloaded: boolean; reloading: boolean; busy: boolean; graphRecovery?: boolean; onReload: () => void; onCopy: () => void; onDiscard: () => void }) {
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-conflict-title"><button className="modal-backdrop" aria-label="保留提示" /><section className="modal-card compact"><header><div><span>草稿冲突</span><h2 id="draft-conflict-title">草稿版本已过期</h2></div></header><div className="modal-body"><div className="notice warning"><strong>草稿已保护，不会强制覆盖</strong><span>{graphRecovery ? "原图草稿仍保留。可在当前版本明确恢复为新草稿，原始种子仍需验证；之前的确认与安装不会恢复。" : serverReloaded ? "已重新加载服务器上保存的项目内容。冲突草稿仍保留，可另存为独立项目。" : "项目内容或草稿的保存版本已变化。可重新加载项目查看，或将保留的草稿复制为新项目；复制时会一并保存该草稿所需的前序内容，不会复制原项目的任务、审核决定或媒体。"}</span></div></div><footer><Button variant="quiet" disabled={busy || reloading || serverReloaded} onClick={onReload}>{reloading ? "正在重新加载…" : serverReloaded ? "已加载服务器版本" : "重新加载服务器版本"}</Button><Button variant="primary" disabled={busy || reloading} onClick={onCopy}>{graphRecovery ? busy ? "正在恢复…" : "在当前版本恢复图草稿" : busy ? "正在复制…" : "复制草稿为新项目"}</Button><Button variant="danger" disabled={busy || reloading} onClick={onDiscard}>丢弃冲突草稿</Button></footer></section></div>;
}

export { UnsafeDraftDialog } from "./UnsafeDraftDialog";
