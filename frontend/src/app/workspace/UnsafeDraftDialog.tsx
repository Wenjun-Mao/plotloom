import { useState } from "react";
import { Button, ErrorNotice } from "../../components";
import type { DraftRecord } from "../../draft-registry";
import type { UnsafeDraft } from "./useWorkspaceSession";

/** Retained author text is inspectable without adopting any project authority. */
export function UnsafeDraftDialog({ reason, records, busy, onKeep, onRetry, onDiscard }: {
  reason: UnsafeDraft["reason"]; records: DraftRecord[]; busy: boolean;
  onKeep: () => void; onRetry: () => void; onDiscard: () => void;
}) {
  const [error, setError] = useState("");
  const text = JSON.stringify(records, null, 2);
  const exportText = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `plotloom-retained-drafts-${records[0]?.projectId ?? "project"}.json`; link.click();
    URL.revokeObjectURL(url);
  };
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="unsafe-draft-title">
    <section className="modal-card"><header><h2 id="unsafe-draft-title">{reason === "archived" ? "归档项目草稿不可恢复" : reason === "missing" ? "原项目不存在，草稿已保留" : "暂时无法核实项目，草稿已保留"}</h2></header>
      <div className="modal-body"><div className="notice warning"><strong>保留内容可查看、复制或导出</strong><span>未核实项目与版本前不会恢复或写入。归档或已删除项目保持不可写；版本变化需要另行处理，不会自动合并。</span></div>
        <label>保留的草稿（只读，含项目、阶段与原版本）<textarea aria-label="保留的草稿" readOnly rows={14} value={text} /></label>
        {error && <ErrorNotice message={error} />}
      </div><footer>
        <Button disabled={busy} onClick={() => void navigator.clipboard.writeText(text).catch(() => setError("复制失败，请从只读文本框选择并复制，或导出文件。"))}>复制保留内容</Button>
        <Button disabled={busy} onClick={exportText}>导出保留内容</Button>
        <Button disabled={busy} onClick={onKeep}>保留草稿，稍后重试</Button>
        <Button variant="primary" disabled={busy} onClick={onRetry}>{busy ? "正在核实…" : "重试核实项目"}</Button>
        <Button variant="danger" disabled={busy} onClick={onDiscard}>丢弃不可用草稿</Button>
      </footer>
    </section>
  </div>;
}
