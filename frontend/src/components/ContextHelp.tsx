import { createContext, useContext, useId, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";

type HelpState = { id: string; hovered: boolean; focused: boolean; pinned: boolean };
const HelpContext = createContext<{ active: HelpState | null; setActive: Dispatch<SetStateAction<HelpState | null>> } | null>(null);

/** One explanation owns the shared compact dock, including pinned help. */
export function ContextHelpGroup({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<HelpState | null>(null);
  return <HelpContext.Provider value={{ active, setActive }}>{children}</HelpContext.Provider>;
}

/** A focusable trigger exposes the same help to pointer, keyboard and touch. */
export function ContextHelp({ label, children }: { label: string; children: string }) {
  const id = useId();
  const group = useContext(HelpContext);
  if (!group) throw new Error("ContextHelp requires a ContextHelpGroup");
  const { active, setActive } = group;
  const open = active?.id === id;
  const update = (change: Partial<Omit<HelpState, "id">>, activate = false) => setActive(current => {
    if (current?.id !== id && !activate) return current;
    // Incidental pointer movement or layout changes cannot replace focused/pinned help.
    if (current?.id !== id && change.hovered && (current?.focused || current?.pinned)) return current;
    const next = { ...(current?.id === id ? current : { id, hovered: false, focused: false, pinned: false }), ...change };
    return next.hovered || next.focused || next.pinned ? next : null;
  });
  const close = () => setActive(current => current?.id === id ? null : current);
  return <span className="context-help" onMouseEnter={() => update({ hovered: true }, true)} onMouseLeave={() => update({ hovered: false })}>
    <button type="button" aria-label={`说明：${label}`} aria-describedby={id} aria-expanded={open} onFocus={() => update({ focused: true }, true)} onBlur={() => update({ focused: false })} onClick={event => {
      if (open && active.pinned) { close(); event.currentTarget.blur(); }
      else update({ pinned: true }, true);
    }} onKeyDown={event => { if (event.key === "Escape") { close(); event.currentTarget.blur(); } }}>?</button>
    <span role="tooltip" id={id} hidden={!open}>{children}</span>
  </span>;
}
