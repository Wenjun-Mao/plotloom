import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BranchingVideoPreview } from "../src/branching-video-preview";
import { plotloomApi } from "../src/api";
import type { ProductionBridgeState, SceneBeatPlan, Shot, StoryGraph, Storyboard, VideoJob } from "../src/types";
import { bridgeState } from "./production-bridge-fixture";
import { bindBridgePlayback } from "./bridge-playback-fixtures";
import { selectedJob } from "./video-pilot-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root; let host: HTMLDivElement;
const choice = { choiceId: "choice", sectionId: "decision", prompt: "Which ending?", outcomes: [{ outcomeId: "a", endingSectionId: "left", label: "Left", consequence: "left ending" }, { outcomeId: "b", endingSectionId: "right", label: "Right", consequence: "right ending" }] };

const graph: StoryGraph = { startNodeId: "decision", nodes: ["decision", "left", "right"].map(id => ({ id, title: id, summary: "", footageMode: "footage" as const, kind: id === "decision" ? "decision" : "ending" })), edges: choice.outcomes.map(outcome => ({ id: outcome.outcomeId, sourceNodeId: "decision", targetNodeId: outcome.endingSectionId, choiceText: outcome.label, kind: "choice", stateEffects: {}, entityStateEffects: [] })), joinContracts: [] };
const storyboard: Storyboard = { shots: graph.nodes.map(node => ({ id: node.id, sceneId: node.id, order: 1, durationUnits: 6000 }) as Shot), shotBeatLinks: [] };
const sceneBeats = { scenes: graph.nodes.map(node => ({ id: node.id, storyNodeId: node.id, order: 1 })), beats: [], dialogueCues: [] } as unknown as SceneBeatPlan;
const fixture = (projectId = "project", revision = 1) => bindBridgePlayback(graph.nodes.map((node,index) => selectedJob(node.id,index + 1,
  { projectId, snapshot: { shot: { id: node.id, sceneId: node.id } } })),sceneBeats.scenes,[choice],revision);
const accepted = bridgeState({ status: "accepted", installation: fixture().installation });
const render = (projectId = "project", revision = 1) => act(async () => root.render(createElement(BranchingVideoPreview,
  { projectId, jobs: fixture(projectId,revision).jobs, graph, storyboard, sceneBeats })));
const retry = () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "重试核对选择界面")!;
const deferred = <T,>() => { let resolve!: (value: T) => void; let reject!: (reason: Error) => void; const promise = new Promise<T>((r, j) => { resolve = r; reject = j; }); return { promise, resolve, reject }; };
beforeEach(() => { vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async projectId => ({ jobs: fixture(projectId,projectId === "other" ? 2 : 1).jobs })); host = document.createElement("div"); root = createRoot(host); vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {}); });
afterEach(async () => { await act(async () => root.unmount()); vi.restoreAllMocks(); });

it("recovers failed reads by explicit retry without bypassing node completion", async () => {
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockRejectedValueOnce(new Error("network failed")).mockResolvedValue(accepted);
  await render();
  expect(host.textContent).toContain("选择界面读取失败"); expect(host.textContent).not.toContain("正在核对");
  await act(async () => retry().click());
  expect(read).toHaveBeenCalledTimes(2); expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => host.querySelector("video")!.dispatchEvent(new Event("ended", { bubbles: true })));
  expect(host.querySelector('[data-testid="branching-choice-question"]')?.textContent).toBe("Which ending?");
});

it.each(["source", "edge"])("keeps %s mismatch closed with a read-only retry", async defect => {
  const stale = { ...accepted, installation: defect === "source" ? { ...fixture().installation, admissionId: "other-installation", status: "outdated" as const, staleReasons: ["source changed"] } : { ...fixture().installation, runtimeChoice: { choices: [{ ...choice, outcomes: [{ ...choice.outcomes[0], label: "foreign" }, choice.outcomes[1]] }] } } };
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(stale);
  await render();
  expect(host.textContent).toContain("不一致"); expect(retry()).toBeDefined();
  expect(host.querySelector("video")).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
});

it("rejects late retry responses after playback ownership changes", async () => {
  const old = deferred<ProductionBridgeState>(); const current = deferred<ProductionBridgeState>();
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockRejectedValueOnce(new Error("failed")).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise);
  await render(); await act(async () => retry().click());
  await render("other", 2);
  await act(async () => old.resolve(accepted));
  expect(host.querySelector("video")).toBeNull();
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => current.resolve({ ...accepted, installation: { ...fixture("other",2).installation, runtimeChoice: { choices: [{ ...choice, prompt: "Current question" }] } } }));
  expect(host.querySelector('[data-testid="branching-choices"]')).toBeNull();
  await act(async () => host.querySelector("video")!.dispatchEvent(new Event("ended", { bubbles: true })));
  expect(host.querySelector('[data-testid="branching-choice-question"]')?.textContent).toBe("Current question");
  expect(read).toHaveBeenCalledTimes(3);
});
