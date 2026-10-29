export function automaticRetryCount(value: string): number | undefined {
  if (!/^\d+$/.test(value)) return undefined;
  const count = Number(value);
  return Number.isSafeInteger(count) ? count : undefined;
}

export function AutomaticRetryCount({ value, onChange, disabled }: {
  value: string; onChange: (value: string) => void; disabled: boolean;
}) {
  const valid = automaticRetryCount(value) !== undefined;
  return <label className="field">自动重试次数<input type="number" min="0" step="1" value={value}
    disabled={disabled} aria-invalid={!valid} onChange={event => onChange(event.target.value)} />
    <small>默认重试 1 次，首次尝试不计入；0 为关闭。每次仍受本次预算限制。结果不确定时，重试可能重复生成并产生费用。</small>
    {!valid && <small role="alert">请输入不小于 0 的整数。</small>}
  </label>;
}
