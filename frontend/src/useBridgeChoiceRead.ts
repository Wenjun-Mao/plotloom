import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { RuntimeChoice, StoryEdge } from "./types";

type ChoiceRead = { identity: string; status: "loading" | "ready" | "failed" | "stale"; choice: RuntimeChoice | null; error?: string };

/** Read-only choice admission belongs to the exact playback/source identity. */
export function useBridgeChoiceRead(projectId: string, identity: string, bridgeOwned: boolean, edges: StoryEdge[], currentNodeId: string) {
  const readIdentity = JSON.stringify([identity, currentNodeId]);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ChoiceRead>({ identity: "", status: "loading", choice: null });
  const owner = useRef({ identity, epoch: 0 });
  useLayoutEffect(() => {
    owner.current = { identity: readIdentity, epoch: owner.current.epoch + 1 };
    return () => { owner.current = { ...owner.current, epoch: owner.current.epoch + 1 }; };
  }, [readIdentity]);
  useEffect(() => {
    if (!bridgeOwned) return;
    const captured = owner.current;
    const controller = new AbortController();
    const current = () => owner.current === captured && !controller.signal.aborted;
    setState({ identity: readIdentity, status: "loading", choice: null });
    void plotloomApi.getProductionBridge(projectId, controller.signal).then(next => {
      if (!current()) return;
      const raw = next.runtimeChoice;
      const choices = raw ? raw.choices : [];
      const admitted = choices.every(choice => {
      const outgoing = edges.filter(edge => edge.sourceNodeId === choice.sectionId && edge.kind === "choice");
      return choice.outcomes.length >= 2 && new Set(choice.outcomes.map(outcome => outcome.outcomeId)).size === choice.outcomes.length
        && outgoing.length === choice.outcomes.length
        && choice.outcomes.every(outcome => outgoing.some(edge => edge.id === outcome.outcomeId && edge.targetNodeId === outcome.endingSectionId && edge.choiceText === outcome.label));
      });
      const graphChoiceSources = new Set(edges.filter(edge => edge.kind === "choice").map(edge => edge.sourceNodeId));
      const exact = next.status === "accepted" && next.installedStoryboardCurrent && admitted
        && new Set(choices.map(choice => choice.sectionId)).size === choices.length
        && choices.length === graphChoiceSources.size && choices.every(choice => graphChoiceSources.has(choice.sectionId));

      setState(exact ? { identity: readIdentity, status: "ready", choice: choices.find(choice => choice.sectionId === currentNodeId) || null } : { identity: readIdentity, status: "stale", choice: null });
    }).catch(reason => {
      if (current()) setState({ identity: readIdentity, status: "failed", choice: null, error: reason instanceof Error ? reason.message : "读取失败" });
    });
    return () => controller.abort();
  }, [projectId, identity, attempt, currentNodeId, bridgeOwned]);
  const read = state.identity === readIdentity ? state : { identity: readIdentity, status: "loading" as const, choice: null };
  return { ...read, retry: () => setAttempt(current => current + 1) };
}
