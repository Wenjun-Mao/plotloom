import { useState } from "react";
import type { PipelineRun, RunExecutionTrace, RunProgress, ServerStageName, TraceEvent } from "../types";
import { stageLabels, summarizeWorkUnitStatuses, toggleContiguousStageRange } from "../model";
import { Badge, Button, EmptyState, JsonPreview, PageHeader, Panel, Spinner } from "../components";
import { canRequestRunCancellation, runCancellationLabel, runStatusLabels, traceKindLabels, traceStatusLabels, workUnitStatusLabels } from "../run-presentation";

function progressElapsed(attempt: RunProgress["workUnits"][number]["latestAttempt"]): string {
  if (!attempt) return "—";
  if (attempt.durationMs != null) return `${attempt.durationMs}ms`;
  if (!attempt.startedAt || !attempt.finishedAt) return attempt.status === "running" ? "运行中" : "—";
  const elapsed = Date.parse(attempt.finishedAt) - Date.parse(attempt.startedAt);
  return Number.isFinite(elapsed) && elapsed >= 0 ? `${elapsed}ms` : "—";
}

export function TracePage({ run, progress, trace, executionTrace, running, onRun, onResume, onCancel }: { run?: PipelineRun; progress?: RunProgress; trace: TraceEvent[]; executionTrace?: RunExecutionTrace; running: boolean; onRun: (stages: ServerStageName[]) => Promise<void>; onResume: () => Promise<void>; onCancel: () => Promise<void> }) {
  const [selectedStages, setSelectedStages] = useState<ServerStageName[]>(["story_bible", "story_graph", "scene_beats", "storyboard"]);
  const [selectedId, setSelectedId] = useState(trace.at(-1)?.id || "");
  const [promptTab, setPromptTab] = useState<"system" | "user" | "payload">("user");
  const selected = trace.find((event) => event.id === selectedId) || trace.at(-1);
  const currentStage = [...trace].reverse().find((event) => event.status === "pending")?.stage;
  const toggle = (stage: ServerStageName) => setSelectedStages((current) => toggleContiguousStageRange(current, stage));
  return <div className="page">
    <PageHeader title="运行轨迹" description="请求、提示词、原始响应、校验与保存记录按顺序保留；请求成功不等于内容通过校验。" actions={running ? <>{run?.status === "queued" && <Button onClick={() => void onResume()}>继续排队运行</Button>}<Button variant="danger" disabled={!canRequestRunCancellation(run)} onClick={() => void onCancel()}>{runCancellationLabel(run)}</Button></> : <Button variant="primary" disabled={!selectedStages.length} onClick={() => void onRun(selectedStages)}>运行所选阶段</Button>} />
    <Panel className="run-console">
      <div className="stage-selector">{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => <label key={stage}><input type="checkbox" checked={selectedStages.includes(stage)} onChange={() => toggle(stage)} /><span>{stageLabels[stage]}</span></label>)}</div>
      <div className="run-state"><Badge tone={run?.status === "failed" ? "danger" : run?.status === "quarantined" ? "warning" : running ? "accent" : "neutral"}>{run ? runStatusLabels[run.status] : "尚未启动"}</Badge>{running && <Spinner label={run?.status === "cancel_requested" ? "正在等待运行结束" : currentStage ? `正在执行 ${stageLabels[currentStage]}` : "正在启动"} />}<code>{run?.id || "尚无运行任务"}</code></div>
      {run?.failureCode && <p className="event-detail">{run.failedStage ? `${stageLabels[run.failedStage]} · ` : ""}{run.failureCode}{run.error ? ` · ${run.error}` : ""}</p>}
    </Panel>
    {progress && <Panel className="run-progress-panel">
      <div className="section-title"><span>实时子任务进度</span><strong>{progress.workUnits.length} 个子任务 · {runStatusLabels[progress.status]}</strong></div>
      <p className="event-detail">{trace.length ? "这里仅显示任务进度；提示词、模型回复、验证资料和生成结果，请在下方选择事件后查看。" : "当前暂无可查看的事件详情；请查看上方的任务状态。"}</p>
      <div className="run-progress-units">
        {progress.workUnits.map((unit) => <div key={unit.workUnitId}>
          <strong>{stageLabels[unit.stage]} · #{unit.sequence}</strong>
          <Badge tone={unit.status === "succeeded" ? "ok" : unit.status === "quarantined" || unit.status === "outcome_unknown" ? "warning" : unit.status === "failed" ? "danger" : "neutral"}>{workUnitStatusLabels[unit.status]}</Badge>
          <small>执行次数 {unit.latestAttempt ? `${unit.latestAttempt.attemptNumber}/${unit.maxAttempts}` : `—/${unit.maxAttempts}`} · {progressElapsed(unit.latestAttempt)} · 令牌用量 {unit.latestAttempt?.inputTokens ?? "—"}/{unit.latestAttempt?.outputTokens ?? "—"}</small>
          {unit.latestAttempt?.outcomeCode && <code>{unit.latestAttempt.outcomeCode}</code>}
          {unit.latestAttempt?.sourceAttemptId && <small>更正来源 ← {unit.latestAttempt.sourceAttemptId}</small>}
          {unit.repairEligible && <small>可前往“隔离修复”单独重做此子任务</small>}
          {!unit.repairEligible && unit.repairReasonCode && <small>{unit.repairReasonCode}</small>}
        </div>)}
      </div>
    </Panel>}
    {executionTrace?.storyGraphTopology && <Panel className="topology-trace">
      <div className="section-title"><span>本次运行使用的剧情图结构</span><strong>剧情图 · sha256:{executionTrace.storyGraphTopology.topologyHash.slice(0, 12)}</strong></div>
      <p className="event-detail">对应生成计划 {executionTrace.storyGraphTopology.generationPlanHash.slice(0, 12)} · {summarizeWorkUnitStatuses(executionTrace)} · {executionTrace.sealedAggregates.length} 项已封存汇总</p>
      <JsonPreview value={executionTrace.storyGraphTopology.topology} />
    </Panel>}
    <div className="trace-layout">
      <Panel className="trace-list">
        <div className="section-title"><span>运行事件</span><strong>{trace.length} 个事件</strong></div>
        {!trace.length && (running
          ? <EmptyState title="正在等待运行事件">正在读取当前任务的运行记录；无需再次启动任务。</EmptyState>
          : run
            ? <EmptyState title="当前任务暂无事件记录">请查看上方的任务状态和失败信息；暂无事件记录不代表任务已通过。</EmptyState>
            : <EmptyState title="还没有运行记录">勾选要生成的阶段，再点击“运行所选阶段”启动任务。</EmptyState>)}
        {trace.map((event) => <button key={event.id} className={`trace-event ${event.id === selected?.id ? "active" : ""}`} onClick={() => setSelectedId(event.id)}><span className={`trace-dot ${event.status}`} /><time>{event.at}</time><div><small>{stageLabels[event.stage]} · {traceKindLabels[event.kind]}</small><strong>{event.title}</strong></div></button>)}
      </Panel>
      <Panel className="prompt-inspector">
        <div className="section-title"><span>事件详情</span><strong>{selected?.title || (running ? "正在等待记录" : "暂无事件详情")}</strong></div>
        {selected ? <>
          <div className="inspector-meta"><Badge tone={selected.status === "error" ? "danger" : selected.status === "warning" ? "warning" : selected.status === "pending" ? "accent" : "ok"}>{traceStatusLabels[selected.status]}</Badge><code>{selected.stage} / {selected.kind}</code></div>
          {selected.detail && <p className="event-detail">{selected.detail}</p>}
          <div className="tabs" role="tablist" aria-label="运行详情">
            {(["system", "user", "payload"] as const).map((tab) => <button role="tab" aria-selected={promptTab === tab} key={tab} onClick={() => setPromptTab(tab)}>{tab === "system" ? "系统提示词" : tab === "user" ? "任务提示词" : "事件数据"}</button>)}
          </div>
          <div role="tabpanel" className="prompt-panel">
            <JsonPreview value={promptTab === "system" ? selected.systemPrompt || "此事件没有系统提示词。" : promptTab === "user" ? selected.userPrompt || "此事件没有任务提示词。" : selected.payload || { note: "此事件没有结构化数据。" }} />
          </div>
        </> : <EmptyState title={running ? "正在等待事件详情" : "暂无事件详情"}>{running
          ? "收到运行记录后，可以在这里查看详情；无需再次启动任务。"
          : run ? "当前任务尚无可查看的事件；请查看上方的任务状态和失败信息。"
          : "任务启动后，运行详情会显示在这里。"}</EmptyState>}
      </Panel>
    </div>
  </div>;
}
