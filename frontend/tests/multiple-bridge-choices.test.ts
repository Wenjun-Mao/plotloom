import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { useBridgeChoiceRead } from "../src/useBridgeChoiceRead";
import type { ProductionBridgeState, RuntimeChoice, StoryEdge } from "../src/types";
import { bridgeState, installedProduction } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const choices: RuntimeChoice[] = [2, 3].map((count, question) => ({ choiceId: `decision-${question}`, sectionId: `decision-${question}`, prompt: `Question ${question}`, outcomes: Array.from({ length: count }, (_, option) => ({ outcomeId: `option-${question}-${option}`, endingSectionId: `next-${question}-${option}`, label: `Option ${option}`, consequence: "Explicit subsequent story" })) }));
const edges: StoryEdge[] = choices.flatMap(choice => choice.outcomes.map(option => ({ id: option.outcomeId, sourceNodeId: choice.sectionId, targetNodeId: option.endingSectionId, choiceText: option.label, kind: "choice" as const, stateEffects: {}, entityStateEffects: [] })));
const accepted = bridgeState({ status: "accepted", installation: installedProduction({ runtimeChoice: { choices } }) });

it("admits every question and changes the displayed question only for the current node", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  let release!: (value: ProductionBridgeState) => void;
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(accepted).mockReturnValueOnce(new Promise(resolve => { release = resolve; }));
  function Reader({ node }: { node: string }) { const value = useBridgeChoiceRead("project", "same-production", true, edges, node); return createElement("div", null, `${value.status}: ${value.choice?.prompt || ""} ${value.choice?.outcomes.length || 0}`); }
  try {
    await act(async () => root.render(createElement(Reader, { node: "decision-0" })));
    expect(host.textContent).toBe("ready: Question 0 2");
    await act(async () => root.render(createElement(Reader, { node: "decision-1" })));
    expect(host.textContent).toBe("loading:  0");
    await act(async () => release(accepted));
    expect(host.textContent).toBe("ready: Question 1 3");
    expect(read).toHaveBeenCalledTimes(2);
  } finally { await act(async () => root.unmount()); vi.restoreAllMocks(); }
});

it("rejects duplicated questions that omit another canonical choice source", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ ...accepted, installation: installedProduction({ runtimeChoice: { choices: [choices[0], choices[0]] } }) });
  function Reader() { const value = useBridgeChoiceRead("project", "production", true, edges, "decision-0"); return createElement("div", null, value.status); }
  try {
    await act(async () => root.render(createElement(Reader)));
    expect(host.textContent).toBe("stale");
  } finally { await act(async () => root.unmount()); vi.restoreAllMocks(); }
});

it.each(["ready", "stale"] as const)("keeps the installed choice authoritative while latest proposal is %s", async status => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue({ ...accepted, status });
  function Reader() { const value = useBridgeChoiceRead("project", "production", true, edges, "decision-0"); return createElement("div", null, `${value.status}: ${value.choice?.prompt}`); }
  try {
    await act(async () => root.render(createElement(Reader)));
    expect(host.textContent).toBe("ready: Question 0");
  } finally { await act(async () => root.unmount()); vi.restoreAllMocks(); }
});
