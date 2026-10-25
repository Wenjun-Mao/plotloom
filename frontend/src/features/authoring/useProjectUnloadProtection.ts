import { useEffect } from "react";
import { hasUnpreservedDrafts } from "../../draft-registry";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";

/** Browser departure follows the current project, including pending File owners. */
export function useProjectUnloadProtection(projectId: string | undefined, quiescence: ProjectDraftQuiescence) {
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!hasUnpreservedDrafts(projectId) && (!projectId || quiescence.locallyPreserved(projectId))) return;
      event.preventDefault(); event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [projectId, quiescence]);
}
