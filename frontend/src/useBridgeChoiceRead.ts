import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { RuntimeChoice, StoryEdge } from "./types";

type ChoiceRead = { identity: string; status: "loading" | "ready" | "failed" | "stale"; choice: RuntimeChoice | null; error?: string };

/** Read-only choice admission belongs to the exact playback/source identity. */
export function useBridgeChoiceRead(projectId: string, identity: string, bridgeOwned: boolean, edges: StoryEdge[]) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ChoiceRead>({ identity: "", status: "loading", choice: null });
  const owner = useRef({ identity, epoch: 0 });
  useLayoutEffect(() => {
    owner.current = { identity, epoch: owner.current.epoch + 1 };
    return () => { owner.current = { ...owner.current, epoch: owner.current.epoch + 1 }; };
  }, [identity]);
  useEffect(() => {
    if (!bridgeOwned) return;
    const captured = owner.current;
    const controller = new AbortController();
    const current = () => owner.current === captured && !controller.signal.aborted;
    setState({ identity, status: "loading", choice: null });
    void plotloomApi.getProductionBridge(projectId, controller.signal).then(next => {
      if (!current()) return;
      const choice = next.runtimeChoice;
      const outgoing = edges.filter(edge => edge.sourceNodeId === choice?.sectionId);
      const exact = choice && next.status === "accepted" && next.installedStoryboardCurrent
        && outgoing.length === choice.outcomes.length
        && choice.outcomes.every(outcome => outgoing.some(edge => edge.id === outcome.outcomeId && edge.targetNodeId === outcome.endingSectionId && edge.choiceText === outcome.label));
      setState(exact ? { identity, status: "ready", choice } : { identity, status: "stale", choice: null });
    }).catch(reason => {
      if (current()) setState({ identity, status: "failed", choice: null, error: reason instanceof Error ? reason.message : "读取失败" });
    });
    return () => controller.abort();
  }, [identity, attempt]);
  const read = state.identity === identity ? state : { identity, status: "loading" as const, choice: null };
  return { ...read, retry: () => setAttempt(current => current + 1) };
}
