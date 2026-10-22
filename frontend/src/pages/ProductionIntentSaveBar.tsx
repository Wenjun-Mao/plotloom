import { Button } from "../components";

/** One section-owned save action; no production confirmation or generation. */
export function ProductionIntentSaveBar({ itemCount, status, disabled, busy, onSave }: {
  itemCount: number; status: string; disabled: boolean; busy: boolean; onSave: () => void;
}) {
  return <div className="bridge-intent-save" role="group" aria-label="戏剧意图整包 · 保存">
    <div className="bridge-intent-save-copy">
      <div><strong>戏剧意图整包 · 共 {itemCount} 项</strong><span role="status">{status}</span></div>
      <p>保存全部条目；不会确认投产或生成媒体。</p>
    </div>
    <Button variant="primary" disabled={disabled} busy={busy} onClick={onSave}>保存戏剧意图整包</Button>
  </div>;
}
