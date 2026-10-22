export function correctionCount(value: string): number | undefined {
  if (!/^\d+$/.test(value)) return undefined;
  const count = Number(value);
  return Number.isSafeInteger(count) ? count : undefined;
}

export function CorrectionCount({ value, onChange, disabled }: { value: string; onChange: (value: string) => void; disabled: boolean }) {
  return <label className="field">每个文字阶段最多自动修正次数<input type="number" min="0" step="1" value={value} disabled={disabled}
    onChange={event => onChange(event.target.value)} />
    <small>默认 1 次；0 为关闭。首次生成不计入，手动追加不会重置次数。</small></label>;
}
