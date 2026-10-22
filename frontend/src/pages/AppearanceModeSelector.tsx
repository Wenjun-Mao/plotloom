import { useId } from "react";

type Mode = "fresh" | "refine";

export function AppearanceModeSelector({ value, disabled, refinementAllowed, onChange }: {
  value: Mode;
  disabled: boolean;
  refinementAllowed: boolean;
  onChange: (mode: Mode) => void;
}) {
  const name = useId();
  return <fieldset className="appearance-mode">
    <legend>生成方式</legend>
    <label><input type="radio" name={name} value="fresh" checked={value === "fresh"} disabled={disabled} onChange={() => onChange("fresh")} />全新生成</label>
    <label><input type="radio" name={name} value="refine" checked={value === "refine"} disabled={disabled || !refinementAllowed} onChange={() => onChange("refine")} />基于图片修改</label>
    {!refinementAllowed && <small>选择可用于修改的候选图片后，才能基于图片修改。</small>}
  </fieldset>;
}
