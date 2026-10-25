import { useState } from "react";
import { Button, ErrorNotice } from "../../components";
import type { RetainedJournalEntry } from "./clientJournalStorage";

/** Every competing journal is addressable; copy/discard never touches another row. */
export function RetainedDraftNotice({ entries, onDiscard, onResume }: {
  entries: RetainedJournalEntry[]; onDiscard: (entry: RetainedJournalEntry) => void | Promise<void>;
  onResume?: (entry: RetainedJournalEntry) => void | Promise<void>;
}) {
  const [error, setError] = useState("");
  if (!entries.length) return null;
  const run = async (action: () => void | Promise<void>) => { try { await action(); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "保留输入未处理。"); } };
  return <section className="notice warning" role="status"><strong>其他会话保留了尚未同步的输入</strong>
    <p>逐份核对归属和版本；不会自动覆盖当前编辑或恢复授权。</p>
    {entries.map(entry => {
      const payload = entry.value.payload as { text?: unknown } | undefined;
      const text = typeof payload?.text === "string" ? payload.text : JSON.stringify(entry.value.value ?? entry.value, null, 2);
      return <details key={`${entry.namespace}:${entry.key}`}><summary>保留输入 · {entry.key}</summary><pre>{text}</pre>
        <div className="button-row"><Button variant="quiet" onClick={() => void navigator.clipboard.writeText(text)}>复制这份输入</Button>
          {onResume && <Button onClick={() => void run(() => onResume(entry))}>作为本会话输入恢复</Button>}
          <Button variant="quiet" onClick={() => void run(() => onDiscard(entry))}>丢弃这份本机输入</Button></div></details>;
    })}{error && <ErrorNotice message={error} />}</section>;
}
