import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { CharacterReferenceProposal, ImageJob, VisualWorkbench } from "../../types";

export type MediaReadPhase = "loading" | "ready" | "error";

const emptyWorkbench: VisualWorkbench = {
  assets: [], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [],
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] }, previews: [],
};
const emptyImageJobs: ImageJob[] = [];
const emptyCharacterProposals: CharacterReferenceProposal[] = [];

function previewKey(projectId: string): string {
  return `plotloom:still-preview:${projectId}`;
}

/** A read is current only after all existing media owners finish for this exact context. */
export function useMediaWorkbenchData({
  projectId, approvalId, approvalRevision, storyboardRevision, shotId,
}: {
  projectId?: string;
  approvalId?: string;
  approvalRevision?: number;
  storyboardRevision?: number;
  shotId?: string;
}) {
  const contextKey = JSON.stringify([projectId, approvalId, approvalRevision, storyboardRevision, shotId]);
  const activeContext = useRef(contextKey);
  activeContext.current = contextKey;
  const sequence = useRef(0);
  const [read, setRead] = useState<{ contextKey: string; phase: MediaReadPhase }>({ contextKey, phase: "loading" });
  const [workbench, setWorkbench] = useState<VisualWorkbench>(emptyWorkbench);
  const [imageJobs, setImageJobs] = useState<ImageJob[]>([]);
  const [characterProposals, setCharacterProposals] = useState<CharacterReferenceProposal[]>([]);
  const [imageExchangeConfigured, setImageExchangeConfigured] = useState(false);
  const [previewId, setPreviewId] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!projectId || activeContext.current !== contextKey) return;
    const request = ++sequence.current;
    const owned = () => !signal?.aborted && request === sequence.current && activeContext.current === contextKey;
    setRead({ contextKey, phase: "loading" });
    try {
      const [next, jobs, proposals] = await Promise.all([
        plotloomApi.getVisualWorkbench(projectId, signal),
        plotloomApi.getImageJobs(projectId, signal),
        plotloomApi.getCharacterReferenceProposals(projectId, signal),
      ]);
      if (!owned()) return;
      setWorkbench(next);
      setImageJobs(jobs.jobs);
      setCharacterProposals(proposals.proposals);
      setImageExchangeConfigured(jobs.configured);
      const saved = window.localStorage.getItem(previewKey(projectId));
      setPreviewId(next.previews.find((item) => item.id === saved)?.id ?? next.previews[0]?.id ?? "");
      setRead({ contextKey, phase: "ready" });
    } catch (error) {
      if (owned()) setRead({ contextKey, phase: "error" });
      throw error;
    }
  }, [projectId, contextKey]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => undefined);
    return () => { controller.abort(); sequence.current += 1; };
  }, [refresh]);

  const mediaReadPhase = read.contextKey === contextKey ? read.phase : "loading";
  const current = mediaReadPhase === "ready";
  return {
    workbench: current ? workbench : emptyWorkbench,
    setWorkbench,
    imageJobs: current ? imageJobs : emptyImageJobs,
    characterProposals: current ? characterProposals : emptyCharacterProposals,
    imageExchangeConfigured: current && imageExchangeConfigured,
    previewId: current ? previewId : "", setPreviewId, refresh, mediaReadPhase,
  };
}
