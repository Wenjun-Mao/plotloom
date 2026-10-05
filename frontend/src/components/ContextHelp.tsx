import { useId, useState } from "react";

/** A focusable trigger exposes the same help to pointer, keyboard and touch. */
export function ContextHelp({ label, children }: { label: string; children: string }) {
  const id = useId();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const open = hovered || focused || pinned;
  return <span className="context-help" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
    <button type="button" aria-label={`说明：${label}`} aria-describedby={id} aria-expanded={open} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onClick={event => {
      setPinned(!pinned);
      if (pinned) { setFocused(false); setHovered(false); event.currentTarget.blur(); }
    }} onKeyDown={event => { if (event.key === "Escape") { setPinned(false); setHovered(false); setFocused(false); event.currentTarget.blur(); } }}>?</button>
    <span role="tooltip" id={id} hidden={!open}>{children}</span>
  </span>;
}
