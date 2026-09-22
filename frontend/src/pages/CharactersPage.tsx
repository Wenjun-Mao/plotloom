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
  const castSessionEpochRef = useRef(0);

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

  const castSession = castSessionKey(projectId, castSessionEpoch, castState);
  const castSessionOwner = useRef(castSession);
  castSessionOwner.current = castSession;

  const invalidateCastSession = useCallback(() => {
    const nextEpoch = castSessionEpochRef.current + 1;
    castSessionEpochRef.current = nextEpoch;
    // This ref changes before CastPanel dispatches. Readers and image actions
    // therefore reject the prior session even before React commits this render.
    castSessionOwner.current = castSessionKey(projectId, nextEpoch, castState);
    setCastSessionEpoch(nextEpoch);
    setCastTransitionPending(true);
  }, [castState, projectId]);

  return <section className="page characters-page" data-testid="characters-stage">
    <header className="page-header"><div><h1>角色</h1><p>完善角色文字，再审阅和选择可复用的外观参考。</p></div></header>
    <CastPanel projectId={projectId} readOnly={readOnly} state={castState} loadError={castError} onState={setCastState} onRefresh={refreshCast} onInvalidate={invalidateCastSession} onTransitionComplete={() => setCastTransitionPending(false)} />
    <CharacterReferenceReviewPanel projectId={projectId} readOnly={readOnly} castState={castState} castSession={castSession} castSessionOwner={castSessionOwner} castTransitionPending={castTransitionPending} />
  </section>;
}

function castSessionKey(projectId: string, epoch: number, state: CastReviewState | undefined): string {
  return `${projectId}:${epoch}:${state?.status ?? "loading"}:${state?.acceptedCast?.revision ?? 0}:${state?.acceptedCast?.contentHash ?? ""}`;
}
