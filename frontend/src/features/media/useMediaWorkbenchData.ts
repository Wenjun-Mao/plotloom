import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { ImageJob, VisualWorkbench } from "../../types";

export type MediaReadPhase = "loading" | "ready" | "error";

const emptyWorkbench: VisualWorkbench = {
  assets: [], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [],
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] }, previews: [],
};
const emptyImageJobs: ImageJob[] = [];

function previewKey(projectId: string): string {
  return `plotloom:still-preview:${projectId}`;
}

/** A read is current only after all existing media owners finish for this exact context. */
export function useMediaWorkbenchData({
  projectId, lifecycleRevision, approvalId, approvalRevision, storyboardRevision, shotId,
}: {
  projectId?: string;
  lifecycleRevision?: number;
  approvalId?: string;
  approvalRevision?: number;
  storyboardRevision?: number;
  shotId?: string;
}) {
  const contextKey = JSON.stringify([projectId, lifecycleRevision, approvalId, approvalRevision, storyboardRevision, shotId]);
  const activeContext = useRef(contextKey);
  activeContext.current = contextKey;
  const selectionOwner = useRef({ projectId, revision: 0 });
  if (selectionOwner.current.projectId !== projectId) selectionOwner.current = { projectId, revision: 0 };
  const projectOwner = selectionOwner.current;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const sequence = useRef(0);
  const [read, setRead] = useState<{ contextKey: string; phase: MediaReadPhase }>({ contextKey, phase: "loading" });
  const [workbench, setWorkbench] = useState<VisualWorkbench>(emptyWorkbench);
  const [imageJobs, setImageJobs] = useState<ImageJob[]>([]);
  const [imageExchangeConfigured, setImageExchangeConfigured] = useState(false);
  const [previewId, setPreviewId] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!projectId || activeContext.current !== contextKey) return;
    const request = ++sequence.current;
    const owned = () => !signal?.aborted && request === sequence.current && activeContext.current === contextKey;
    setRead({ contextKey, phase: "loading" });
    try {
      const [next, jobs] = await Promise.all([
        plotloomApi.getVisualWorkbench(projectId, signal),
        plotloomApi.getImageJobs(projectId, signal),
      ]);
      if (!owned()) return;
      if (next.selectionRevision < projectOwner.revision) throw new Error("媒体读取版本落后于已确认的选择；请重新读取。");
      projectOwner.revision = next.selectionRevision;
      setWorkbench(next);
      setImageJobs(jobs.jobs);
      setImageExchangeConfigured(jobs.configured);
      const saved = window.localStorage.getItem(previewKey(projectId));
      setPreviewId(next.previews.find((item) => item.id === saved)?.id ?? next.previews[0]?.id ?? "");
      setRead({ contextKey, phase: "ready" });
    } catch (error) {
      if (owned()) setRead({ contextKey, phase: "error" });
      throw error;
    }
  }, [projectId, contextKey, projectOwner]);

  const currentRefresh = useRef(refresh);
  currentRefresh.current = refresh;
  const refreshAfterProjectWrite = useCallback(async () => {
    if (!mounted.current || selectionOwner.current !== projectOwner) return;
    // Assets belong to the project, not the shot/approval that started a write.
    // Supersede reads begun before its ACK using this visit's current context.
    await currentRefresh.current();
  }, [projectOwner]);
  const acknowledgeSelectionRevision = useCallback(async (revision: number) => {
    if (!mounted.current || selectionOwner.current !== projectOwner) return;
    projectOwner.revision = Math.max(projectOwner.revision, revision);
    // Selection is project-wide even if its shot changed while saving. Start a
    // read for the current context, superseding snapshots begun before this ACK.
    // Only that complete read may publish bindings and enable media controls.
    await refreshAfterProjectWrite();
  }, [projectOwner, refreshAfterProjectWrite]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => undefined);
    return () => { controller.abort(); sequence.current += 1; };
  }, [refresh]);

  const mediaReadPhase = read.contextKey === contextKey ? read.phase : "loading";
  const current = mediaReadPhase === "ready";
  return {
    workbench: current ? workbench : emptyWorkbench,
    acknowledgeSelectionRevision, refreshAfterProjectWrite,
    imageJobs: current ? imageJobs : emptyImageJobs,
    imageExchangeConfigured: current && imageExchangeConfigured,
    previewId: current ? previewId : "", setPreviewId, refresh, mediaReadPhase,
  };
}
