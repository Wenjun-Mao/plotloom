import { useState } from "react";
import type { PipelineRun, RunExecutionTrace, RunProgress, ServerStageName, TraceEvent } from "../types";
import { stageLabels, summarizeWorkUnitStatuses, toggleContiguousStageRange } from "../model";
import { Badge, Button, EmptyState, JsonPreview, PageHeader, Panel, Spinner } from "../components";

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
    <PageHeader eyebrow="06 · Provenance" title="运行轨迹与 Prompt Inspector" description="请求、提示词、原始响应、验证与安装事件按顺序保留；HTTP 成功不等于内容通过。" actions={running ? <>{run?.status === "queued" && <Button onClick={() => void onResume()}>继续排队运行</Button>}<Button variant="danger" onClick={() => void onCancel()}>取消运行</Button></> : <Button variant="primary" disabled={!selectedStages.length} onClick={() => void onRun(selectedStages)}>运行所选阶段</Button>} />
    <Panel className="run-console">
      <div className="stage-selector">{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => <label key={stage}><input type="checkbox" checked={selectedStages.includes(stage)} onChange={() => toggle(stage)} /><span>{stageLabels[stage]}</span></label>)}</div>
      <div className="run-state"><Badge tone={run?.status === "failed" ? "danger" : run?.status === "quarantined" ? "warning" : running ? "accent" : "neutral"}>{run?.status || "idle"}</Badge>{running && <Spinner label={currentStage ? `正在执行 ${stageLabels[currentStage]}` : "正在启动"} />}<code>{run?.id || "no active run"}</code></div>
      {run?.failureCode && <p className="event-detail">{run.failedStage ? `${stageLabels[run.failedStage]} · ` : ""}{run.failureCode}{run.error ? ` · ${run.error}` : ""}</p>}
    </Panel>
    {progress && <Panel className="run-progress-panel">
      <div className="section-title"><span>Live work-unit projection</span><strong>{progress.workUnits.length} units · {progress.status}</strong></div>
      <p className="event-detail">轻量轮询投影不含 prompt、模型正文、验证 payload 或 artifact 内容。证据仅在下方按需加载。</p>
      <div className="run-progress-units">
        {progress.workUnits.map((unit) => <div key={unit.workUnitId}>
          <strong>{stageLabels[unit.stage]} · #{unit.sequence}</strong>
          <Badge tone={unit.status === "succeeded" ? "ok" : unit.status === "quarantined" || unit.status === "outcome_unknown" ? "warning" : unit.status === "failed" ? "danger" : "neutral"}>{unit.status}</Badge>
          <small>Attempt {unit.latestAttempt ? `${unit.latestAttempt.attemptNumber}/${unit.maxAttempts}` : `—/${unit.maxAttempts}`} · {progressElapsed(unit.latestAttempt)} · token {unit.latestAttempt?.inputTokens ?? "—"}/{unit.latestAttempt?.outputTokens ?? "—"}</small>
          {unit.latestAttempt?.outcomeCode && <code>{unit.latestAttempt.outcomeCode}</code>}
          {unit.latestAttempt?.sourceAttemptId && <small>correction ← {unit.latestAttempt.sourceAttemptId}</small>}
          {unit.repairEligible && <small>可前往隔离修复精确修复此 unit</small>}
          {!unit.repairEligible && unit.repairReasonCode && <small>{unit.repairReasonCode}</small>}
        </div>)}
      </div>
    </Panel>}
    {executionTrace?.storyGraphTopology && <Panel className="topology-trace">
      <div className="section-title"><span>Frozen topology</span><strong>story graph · sha256:{executionTrace.storyGraphTopology.topologyHash.slice(0, 12)}</strong></div>
      <p className="event-detail">Bound to generation plan {executionTrace.storyGraphTopology.generationPlanHash.slice(0, 12)} · {summarizeWorkUnitStatuses(executionTrace)} · {executionTrace.sealedAggregates.length} sealed aggregates</p>
      <JsonPreview value={executionTrace.storyGraphTopology.topology} />
    </Panel>}
    <div className="trace-layout">
      <Panel className="trace-list">
        <div className="section-title"><span>Event stream</span><strong>{trace.length} 个事件</strong></div>
        {!trace.length && <EmptyState title="还没有运行记录">选择阶段并启动一次 pipeline run。</EmptyState>}
        {trace.map((event) => <button key={event.id} className={`trace-event ${event.id === selected?.id ? "active" : ""}`} onClick={() => setSelectedId(event.id)}><span className={`trace-dot ${event.status}`} /><time>{event.at}</time><div><small>{stageLabels[event.stage]} · {event.kind}</small><strong>{event.title}</strong></div></button>)}
      </Panel>
      <Panel className="prompt-inspector">
        <div className="section-title"><span>Inspector</span><strong>{selected?.title || "选择事件"}</strong></div>
        {selected ? <>
          <div className="inspector-meta"><Badge tone={selected.status === "error" ? "danger" : selected.status === "warning" ? "warning" : "ok"}>{selected.status}</Badge><code>{selected.stage} / {selected.kind}</code></div>
          {selected.detail && <p className="event-detail">{selected.detail}</p>}
          <div className="tabs" role="tablist" aria-label="Prompt 视图">
            {(["system", "user", "payload"] as const).map((tab) => <button role="tab" aria-selected={promptTab === tab} key={tab} onClick={() => setPromptTab(tab)}>{tab === "system" ? "System" : tab === "user" ? "User" : "Payload"}</button>)}
          </div>
          <div role="tabpanel" className="prompt-panel">
            <JsonPreview value={promptTab === "system" ? selected.systemPrompt || "此事件没有 system prompt。" : promptTab === "user" ? selected.userPrompt || "此事件没有 user prompt。" : selected.payload || { note: "此事件没有结构化 payload。" }} />
          </div>
        </> : <EmptyState title="选择一个事件">这里会显示精确 prompt 与验证上下文。</EmptyState>}
      </Panel>
    </div>
  </div>;
}
