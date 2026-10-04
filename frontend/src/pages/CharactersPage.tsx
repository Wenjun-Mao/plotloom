import { useCallback, useEffect, useRef, useState } from "react";

import { plotloomApi } from "../api";
import type { CastReviewState } from "../types";
import { CastPanel } from "./CastPanel";
import { CharacterReferenceReviewPanel } from "./CharacterReferenceGalleryPage";
import { Button } from "../components";
import { StageGuide } from "../components/StageGuide";

/** One creator task: settle cast text, then establish appearance for future shots. */
export function CharactersPage({ projectId, readOnly, onContinue }: { projectId: string; readOnly: boolean; onContinue?: () => void }) {
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
    <StageGuide next={onContinue && <Button variant="quiet" disabled={Boolean(castError) || !castState?.acceptedCast || castState.status !== "accepted" || castTransitionPending} onClick={onContinue}>继续：美术参考</Button>}>
      {castError ? "角色设定读取失败，请在下方重试。" : !castState ? "正在读取角色设定，请稍候。" : castState.status === "reopened" ? "先保存或取消角色修改，再继续。已保留的旧版本不代表本次编辑已确认。" : castState.status === "stale" ? "上游故事已变化，请先更新并确认角色设定。" : castState.status === "accepted" && castState.acceptedCast ? "角色文字已确认。可在下方制作和选择外观参考，也可继续整理地点与道具；继续不会自动生成图片。" : "准备角色任务并发送给文字创作助手，审核结果后确认使用。外观参考图片在文字确认后单独制作。"}
    </StageGuide>
    <CastPanel projectId={projectId} readOnly={readOnly} state={castState} loadError={castError} onState={setCastState} onRefresh={refreshCast} onInvalidate={invalidateCastSession} onTransitionComplete={() => setCastTransitionPending(false)} />
    {!castError && <CharacterReferenceReviewPanel projectId={projectId} readOnly={readOnly} castState={castState} castSession={castSession} castSessionOwner={castSessionOwner} castTransitionPending={castTransitionPending} />}
  </section>;
}

function castSessionKey(projectId: string, epoch: number, state: CastReviewState | undefined): string {
  return `${projectId}:${epoch}:${state?.status ?? "loading"}:${state?.acceptedCast?.revision ?? 0}:${state?.acceptedCast?.contentHash ?? ""}`;
}
