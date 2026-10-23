import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { Viewport, XYPosition } from "@xyflow/react";

/** Visual context belongs to the active workspace, never to the authored graph. */
export type ProfessionalPresentation = { positions: Record<string, XYPosition>; viewport?: Viewport };
const Context = createContext<ProfessionalPresentation | null>(null);

export function ProfessionalPresentationProvider({ projectId, children }: { projectId?: string; children: ReactNode }) {
  // A single active project, deliberately not a per-project cache or preference.
  const presentation = useMemo<ProfessionalPresentation>(() => ({ positions: {} }), [projectId]);
  return <Context.Provider value={presentation}>{children}</Context.Provider>;
}

export function useProfessionalPresentation() {
  const shared = useContext(Context);
  const local = useMemo<ProfessionalPresentation>(() => ({ positions: {} }), []);
  return shared ?? local;
}

export const professionalNavigation = {
  zoomOnScroll: false, zoomOnPinch: true, zoomOnDoubleClick: false,
  zoomActivationKeyCode: null, panOnScroll: false, panOnDrag: true, preventScrolling: false,
} as const;
