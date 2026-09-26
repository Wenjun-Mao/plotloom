import type { ReactNode } from "react";

export function CastFieldLabel({ htmlFor, children }: { htmlFor: string; children: ReactNode }) {
  return <label htmlFor={htmlFor} onClick={(event) => {
    const selection = window.getSelection();
    // Preserve a drag-selected label instead of letting Safari's activation
    // transfer focus (and the selection) into its associated control.
    if (selection && !selection.isCollapsed && Array.from({ length: selection.rangeCount }, (_, index) => selection.getRangeAt(index)).some((range) => range.intersectsNode(event.currentTarget))) event.preventDefault();
  }}>{children}</label>;
}
