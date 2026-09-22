import { useEffect, useState } from "react";
import type { QuarantineItem } from "../types";
import { stageLabels } from "../model";
import { Badge, Button, EmptyState, PageHeader, Panel } from "../components";

function elapsed(attempt: QuarantineItem["attempt"]): string {
  if (!attempt) return "尚无 attempt";
  if (attempt.durationMs != null) return `${attempt.durationMs} ms`;
  if (!attempt.finishedAt || !attempt.startedAt) return attempt.status === "running" ? "进行中" : "未记录";
  const value = Date.parse(attempt.finishedAt) - Date.parse(attempt.startedAt);
  return Number.isFinite(value) && value >= 0 ? `${value} ms` : "未记录";
}

function tokenSummary(attempt: QuarantineItem["attempt"]): string {
  if (!attempt) return "Token 未记录";
  return `Token 输入 ${attempt.inputTokens ?? "—"} · 输出 ${attempt.outputTokens ?? "—"}`;
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
    <PageHeader title="隔离修复" description="高频状态只读取轻量 work-unit 投影。Prompt、原始响应与验证证据仅在运行轨迹中按需查看。" />
    {!items.length ? <EmptyState title="隔离区为空">所有阶段输出都已通过合同验证。</EmptyState> : <div className="quarantine-layout">
      <Panel className="quarantine-list">
        {items.map((item) => <button key={item.id} className={item.id === selected?.id ? "active" : ""} onClick={() => setSelectedId(item.id)}><Badge tone={item.status === "outcome_unknown" ? "warning" : "danger"}>{item.code}</Badge><strong>Unit {item.id} · {item.message}</strong><small>{stageLabels[item.stage]} · {item.status || "legacy"}</small></button>)}
      </Panel>
      {selected && <Panel className="repair-panel">
        <div className="section-title"><span>Work-unit status</span><strong>{selected.code}</strong></div>
        <p className="repair-message">{selected.message}</p>
        <dl className="run-progress-meta">
          <div><dt>阶段</dt><dd>{stageLabels[selected.stage]}</dd></div>
          <div><dt>Attempt</dt><dd>{selected.attempt ? `${selected.attempt.attemptNumber}/${selected.maxAttempts ?? 1} · ${selected.attempt.attemptKind}` : "—"}</dd></div>
          <div><dt>耗时</dt><dd>{elapsed(selected.attempt)}</dd></div>
          <div><dt>用量</dt><dd>{tokenSummary(selected.attempt)}</dd></div>
          <div><dt>失败码</dt><dd><code>{selected.attempt?.outcomeCode || selected.code}</code></dd></div>
          <div><dt>来源</dt><dd>{selected.attempt?.sourceAttemptId ? `correction ← ${selected.attempt.sourceAttemptId}` : "primary"}</dd></div>
        </dl>
        {selected.repairEligible ? <>
          <p className="event-detail">修复会继承冻结的父 run 合同与 instructions，只重新执行这个 work unit；同阶段成功 sibling 以不可变绑定复用。</p>
          <Button variant="primary" disabled={repairing} onClick={() => void onRepair(selected)}>{repairing ? "修复中…" : "修复这个 work unit"}</Button>
        </> : <div className="notice"><strong>不能精确修复</strong><span><code>{selected.repairReasonCode || "repair.not_eligible"}</code>。资格由服务端按冻结快照、封存状态和请求结果决定。</span></div>}
        <div className="repair-rebuild-separator"><strong>需要改变整个阶段合同？</strong><span>完整重建会新建阶段运行，与精确 work-unit 修复不同。</span><Button disabled={repairing} onClick={() => void onRebuildStage(selected.stage)}>从本阶段完整重建</Button></div>
      </Panel>}
    </div>}
  </div>;
}
