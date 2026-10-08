import { useEffect, useState } from "react";
import type { QuarantineItem } from "../types";
import { stageLabels } from "../model";
import { Badge, Button, EmptyState, PageHeader, Panel } from "../components";

function elapsed(attempt: QuarantineItem["attempt"]): string {
  if (!attempt) return "尚无执行记录";
  if (attempt.durationMs != null) return `${attempt.durationMs} ms`;
  if (!attempt.finishedAt || !attempt.startedAt) return attempt.status === "running" ? "进行中" : "未记录";
  const value = Date.parse(attempt.finishedAt) - Date.parse(attempt.startedAt);
  return Number.isFinite(value) && value >= 0 ? `${value} ms` : "未记录";
}

function tokenSummary(attempt: QuarantineItem["attempt"]): string {
  if (!attempt) return "令牌用量未记录";
  return `令牌用量：输入 ${attempt.inputTokens ?? "—"} · 输出 ${attempt.outputTokens ?? "—"}`;
}

export function QuarantinePage({ items, repairing, onRepair, onRebuildStage }: {
  items: QuarantineItem[];
  repairing: boolean;
  onRepair: (item: QuarantineItem) => Promise<void>;
  onRebuildStage: (stage: QuarantineItem["stage"]) => Promise<void>;
}) {
  const [selectedId, setSelectedId] = useState(items[0]?.id || "");
  const selected = items.find((item) => item.id === selectedId) || items[0];
  useEffect(() => {
    if (!items.some((item) => item.id === selectedId)) {
      setSelectedId(items[0]?.id || "");
    }
  }, [items, selectedId]);
  return <div className="page">
    <PageHeader title="隔离修复" description="在这里检查需要处理的失败或结果不确定的任务。符合修复条件时，可以只重做其中一个任务；提示词、原始响应和验证详情在“运行轨迹”中查看。" />
    {!items.length ? <EmptyState title="隔离区为空">当前未显示隔离结果。任务仍在运行或尚未读取完成时，不代表所有结果已通过验证。</EmptyState> : <div className="quarantine-layout">
      <Panel className="quarantine-list">
        {items.map((item) => <button key={item.id} className={item.id === selected?.id ? "active" : ""} onClick={() => setSelectedId(item.id)}><Badge tone={item.status === "outcome_unknown" ? "warning" : "danger"}>{item.code}</Badge><strong>子任务 {item.id} · {item.message}</strong><small>{stageLabels[item.stage]} · {item.status || "legacy"}</small></button>)}
      </Panel>
      {selected && <Panel className="repair-panel">
        <div className="section-title"><span>子任务状态</span><strong>{selected.code}</strong></div>
        <p className="repair-message">{selected.message}</p>
        <dl className="run-progress-meta">
          <div><dt>阶段</dt><dd>{stageLabels[selected.stage]}</dd></div>
          <div><dt>执行次数</dt><dd>{selected.attempt ? `${selected.attempt.attemptNumber}/${selected.maxAttempts ?? 1} · ${selected.attempt.attemptKind === "correction" ? "更正执行" : "首次执行"}` : "—"}</dd></div>
          <div><dt>耗时</dt><dd>{elapsed(selected.attempt)}</dd></div>
          <div><dt>用量</dt><dd>{tokenSummary(selected.attempt)}</dd></div>
          <div><dt>失败码</dt><dd><code>{selected.attempt?.outcomeCode || selected.code}</code></dd></div>
          <div><dt>来源</dt><dd>{selected.attempt?.sourceAttemptId ? `更正来源 ← ${selected.attempt.sourceAttemptId}` : "首次执行"}</dd></div>
        </dl>
        {selected.repairEligible ? <>
          <p className="event-detail">修复会沿用该次运行冻结的要求，只重新执行选中的子任务；同一阶段已成功的其他子任务保持原有绑定，不会重新生成。</p>
          <Button variant="primary" disabled={repairing} onClick={() => void onRepair(selected)}>{repairing ? "修复中…" : "重新执行此子任务"}</Button>
        </> : <div className="notice"><strong>暂不能单独修复</strong><span><code>{selected.repairReasonCode || "repair.not_eligible"}</code>。是否符合修复条件由服务端根据冻结快照、封存状态和请求结果判断。</span></div>}
        <div className="repair-rebuild-separator"><strong>需要重新运行本阶段及后续流程？</strong><span>这会从所选阶段开始新建运行，并重新执行后续阶段；与只重做一个子任务不同。</span><Button disabled={repairing} onClick={() => void onRebuildStage(selected.stage)}>重建本阶段及后续阶段</Button></div>
      </Panel>}
    </div>}
  </div>;
}
