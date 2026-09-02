import { useState } from "react";
import type { QuarantineItem } from "../types";
import { stageLabels } from "../model";
import { Badge, Button, EmptyState, Field, JsonPreview, PageHeader, Panel } from "../components";

export function QuarantinePage({ items, repairing, onRepair }: { items: QuarantineItem[]; repairing: boolean; onRepair: (item: QuarantineItem, instruction: string) => Promise<void> }) {
  const [selectedId, setSelectedId] = useState(items[0]?.id || "");
  const selected = items.find((item) => item.id === selectedId);
  const [instruction, setInstruction] = useState(selected?.repairHint || "");
  const choose = (item: QuarantineItem) => { setSelectedId(item.id); setInstruction(item.repairHint); };
  return <div className="page">
    <PageHeader eyebrow="07 · Safe failure boundary" title="隔离区与修复" description="不合约的模型输出不会覆盖项目。原始输出、错误码与修复指令保持绑定。" />
    {!items.length ? <EmptyState title="隔离区为空">所有阶段输出都已通过合同验证。</EmptyState> : <div className="quarantine-layout">
      <Panel className="quarantine-list">
        {items.map((item) => <button key={item.id} className={item.id === selectedId ? "active" : ""} onClick={() => choose(item)}><Badge tone="danger">{item.code}</Badge><strong>{item.message}</strong><small>{stageLabels[item.stage]}</small></button>)}
      </Panel>
      {selected && <Panel className="repair-panel">
        <div className="section-title"><span>Contract rejection</span><strong>{selected.code}</strong></div>
        <p className="repair-message">{selected.message}</p>
        <h3>原始输出</h3><JsonPreview value={selected.rawOutput} />
        <Field label="定向修复指令" hint="修复请求引用隔离输出，不重新猜测已通过的内容。"><textarea rows={5} value={instruction} onChange={(event) => setInstruction(event.target.value)} /></Field>
        <Button variant="primary" disabled={repairing || !instruction.trim()} onClick={() => void onRepair(selected, instruction)}>{repairing ? "修复中…" : "提交修复"}</Button>
      </Panel>}
    </div>}
  </div>;
}
