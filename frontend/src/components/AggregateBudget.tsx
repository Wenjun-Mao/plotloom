import { Field } from "../components";

// Null is unlimited. Finite mode keeps raw text so blank/invalid input never
// silently becomes an unlimited budget or a coerced zero.
export type BudgetInput = string | null;
export function parseBudget(value: BudgetInput, minimum: number): number | null | undefined {
  if (value === null) return null;
  if (!/^[0-9]+$/.test(value)) return undefined;
  const amount = Number(value);
  return Number.isSafeInteger(amount) && amount >= minimum ? amount : undefined;
}
export function budgetSummary(limit: number | null, unit: string): string {
  return limit === null ? "不限" : `${limit} ${unit}`;
}
export function AggregateBudget({ label, value, minimum, onChange, disabled }: {
  label: string; value: BudgetInput; minimum: number; onChange: (value: BudgetInput) => void; disabled?: boolean;
}) {
  const invalid = parseBudget(value, minimum) === undefined;
  return <div><Field label={`${label}预算`}><select value={value === null ? "unlimited" : "finite"}
    disabled={disabled} onChange={event => onChange(event.target.value === "unlimited" ? null : "")}>
    <option value="unlimited">不限（默认）</option><option value="finite">设置有限上限</option>
  </select></Field>
    {value !== null && <Field label={label}><input type="text" inputMode="numeric" value={value}
      aria-invalid={invalid} disabled={disabled} onChange={event => onChange(event.target.value)} />
      {invalid && <span role="status">请输入不小于 {minimum} 的整数。</span>}</Field>}
  </div>;
}
