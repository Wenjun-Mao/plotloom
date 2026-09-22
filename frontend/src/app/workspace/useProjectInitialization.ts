import { useCallback } from "react";
import { demoProject, demoRun, demoTrace } from "../../demo";
import { blankWorkspace } from "./contracts";
import type { WorkspaceSession } from "./useWorkspaceSession";

type ProjectInitializationSession = Pick<WorkspaceSession, "activePage" | "startLocalWorkspace">;

/** Starts a deliberately local blank or teaching project without touching server state. */
export function useProjectInitialization({ session, clearDraftWorkflow }: {
  session: ProjectInitializationSession;
  clearDraftWorkflow: () => void;
}) {
  const startBlankProject = useCallback(() => {
    clearDraftWorkflow();
    session.startLocalWorkspace(
      { project: "", stage: session.activePage, entity: "", run: "", hash: "" },
      { project: blankWorkspace("local-initialization"), connection: "blank", onboarding: false },
    );
  }, [clearDraftWorkflow, session]);
  const openSampleProject = useCallback(() => {
    clearDraftWorkflow();
    session.startLocalWorkspace(
      { project: "", stage: session.activePage, entity: "", run: "", hash: "" },
      {
        project: { ...demoProject, initialStageOnFirstSave: "storyboard" },
        connection: "demo",
        run: demoRun,
        trace: demoTrace,
        onboarding: false,
      },
    );
  }, [clearDraftWorkflow, session]);
  return { startBlankProject, openSampleProject };
}
