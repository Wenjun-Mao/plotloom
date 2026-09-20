import { useCallback, useEffect, useRef, useState } from "react";

import { plotloomApi } from "../api";
import type { CastReviewState } from "../types";
import { CastPanel } from "./CastPanel";
import { CharacterReferenceReviewPanel } from "./CharacterReferenceGalleryPage";

/** One creator task: settle cast text, then establish appearance for future shots. */
export function CharactersPage({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [castState, setCastState] = useState<CastReviewState>();
  const [castError, setCastError] = useState("");
  const [castSessionEpoch, setCastSessionEpoch] = useState(0);
  const [castTransitionPending, setCastTransitionPending] = useState(false);
  const owner = useRef(0);

  const refreshCast = useCallback(async (expectedOwner = owner.current) => {
    if (owner.current !== expectedOwner) return false;
    try {
      const next = await plotloomApi.getCast(projectId);
      if (owner.current !== expectedOwner) return false;
      setCastState(next); setCastError("");
      return true;
    } catch (reason) {
      if (owner.current === expectedOwner) setCastError(reason instanceof Error ? reason.message : "无法读取角色提案。");
      return false;
    }
  }, [projectId]);

  useEffect(() => {
    const requestOwner = ++owner.current;
    setCastState(undefined); setCastError(""); setCastTransitionPending(false);
    void refreshCast(requestOwner);
    return () => { if (owner.current === requestOwner) owner.current += 1; };
  }, [refreshCast]);

  const invalidateCastSession = useCallback(() => {
    setCastSessionEpoch((current) => current + 1);
    setCastTransitionPending(true);
  }, []);

  // The cast session is the shared authority boundary for both text review and
  // image actions.  It changes synchronously with any accepted/reopened cast.
  const castSession = `${projectId}:${castSessionEpoch}:${castState?.status ?? "loading"}:${castState?.acceptedCast?.revision ?? 0}:${castState?.acceptedCast?.contentHash ?? ""}`;
  return <section className="page characters-page" data-testid="characters-stage">
    <header className="page-header"><div><span>角色</span><h1>角色文字与外观</h1><p>先审核角色文字，再用已有图像建立未来镜头可复用的身份参考。候选不会自动成为选择，准备 handoff 也不会自动生成。</p></div></header>
    <CastPanel projectId={projectId} readOnly={readOnly} state={castState} loadError={castError} onState={setCastState} onRefresh={refreshCast} onInvalidate={invalidateCastSession} onTransitionComplete={() => setCastTransitionPending(false)} />
    <CharacterReferenceReviewPanel projectId={projectId} readOnly={readOnly} castState={castState} castSession={castSession} castTransitionPending={castTransitionPending} />
  </section>;
}
