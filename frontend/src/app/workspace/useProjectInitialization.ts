import { useCallback, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { demoProject, demoRun, demoTrace } from "../../demo";
import { blankWorkspace } from "./contracts";
import { initialStagesThrough } from "../../project-creation";
import { acknowledgeCreationIntent, reserveCreationIntent, retainedCreationIntent, type ProjectCreationIntent } from "../../features/authoring/projectCreationIntent";
import type { WorkspaceSession } from "./useWorkspaceSession";

type ProjectInitializationSession = Pick<WorkspaceSession, "activePage" | "startLocalWorkspace" | "capture" | "isCurrent" | "acceptCreatedProject">;

/** New reserves one durable identity; preview has no persistence side effects. */
export function useProjectInitialization({ session, clearDraftWorkflow, reportError }: {
  session: ProjectInitializationSession; clearDraftWorkflow: () => void; reportError?: (message: string) => void;
}) {
  const pending = useRef<ProjectCreationIntent | undefined>(undefined);
  const flight = useRef<Promise<void> | undefined>(undefined);
  const [creating, setCreating] = useState(false);
  const create = useCallback(async (mode: ProjectCreationIntent["mode"]) => {
    if (flight.current) return flight.current;
    const operation = session.capture();
    let intent: ProjectCreationIntent;
    try {
      const retained = pending.current ?? retainedCreationIntent();
      // A different unresolved mode must be retried under its frozen request,
      // never rebound to new content or hidden behind a fresh idempotency key.
      if (retained && retained.mode !== mode) throw new Error("另有尚未确认创建的项目；请先重试原来的空白项目或示例编辑副本。");
      intent = retained ?? reserveCreationIntent(mode, mode === "blank" ? { brief: null } : {
        brief: demoProject.brief, initialStages: initialStagesThrough(demoProject, "storyboard"),
      });
      pending.current = intent;
    } catch (error) { reportError?.(error instanceof Error ? error.message : "创建意图未保留。"); return; }
    setCreating(true);
    flight.current = (async () => {
      try {
        const created = await plotloomApi.createProject(intent.request, intent.key);
        acknowledgeCreationIntent(intent); pending.current = undefined;
        if (!session.isCurrent(operation)) return;
        clearDraftWorkflow();
        session.startLocalWorkspace({ project: "", stage: "brief", entity: "", run: "", hash: "" }, { project: blankWorkspace(), connection: "blank", onboarding: false });
        session.acceptCreatedProject(blankWorkspace(), created, null);
      } catch (error) { if (session.isCurrent(operation)) reportError?.(`新项目尚未确认创建；重试会沿用同一身份。${error instanceof Error ? error.message : ""}`); }
      finally { flight.current = undefined; setCreating(false); }
    })();
    return flight.current;
  }, [session, clearDraftWorkflow, reportError]);
  const startBlankProject = useCallback(() => create("blank"), [create]);
  const createTeachingCopy = useCallback(() => create("teaching"), [create]);
  const openSampleProject = useCallback(() => {
    clearDraftWorkflow();
    session.startLocalWorkspace({ project: "", stage: session.activePage, entity: "", run: "", hash: "" }, {
      project: { ...demoProject, teachingPreview: true }, connection: "demo", run: demoRun, trace: demoTrace, onboarding: false,
    });
  }, [session, clearDraftWorkflow]);
  return { startBlankProject, openSampleProject, createTeachingCopy, creating };
}
