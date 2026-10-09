import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ArtPanel } from "../src/pages/ArtPanel";
import { ScriptPanel } from "../src/pages/ScriptPanel";
import { StoryboardReviewPanel } from "../src/pages/StoryboardReviewPanel";
import type { ArtBinding, ArtReviewState, ScriptBinding, ScriptReviewState, StoryboardReviewBinding, StoryboardReviewState } from "../src/types";

// These unit checks isolate accepted-content authority. Real dispatch/admission
// and production preparation are exercised by their independent API/browser tests.
vi.mock("../src/features/specialists/SpecialistTaskActions", () => ({ SpecialistTaskActions: () => createElement("p", null, "current candidate task") }));
vi.mock("../src/pages/ProductionBridgePanel", () => ({ ProductionBridgePanel: ({ readOnly }: { readOnly: boolean }) => createElement("button", { disabled: readOnly }, "production bridge") }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

const diagnostic = { code: "binding_revision_changed", owner: "art", field: "art_revision", technicalMessage: "accepted art revision changed" } as const;
const evidence = { status: "retained", staleReasons: [diagnostic] } as const;
const identity = { revision: 1, candidateJobId: "old", contentHash: "old-content", acceptedAt: "2026-10-09T00:00:00Z" };
const baseCandidate = { jobId: "new", deliveryId: null, manifestHash: null, reportAvailable: false, createdAt: identity.acceptedAt, deliveredAt: null };

it.each([ ["prepared", "opening"], ["prepared", "choice"], ["ready", "opening"], ["ready", "choice"] ] as const)("fresh %s Script candidate cannot reopen or relabel retained %s evidence", async (status, sectionId) => {
  const binding: ScriptBinding = {
    sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline",
    sectionMapRevision: 1, sectionMapContentHash: "map", graphRevision: 1, graphContentHash: "graph",
    sectionIds: ["opening", "choice"], castRevision: 1, castContentHash: "cast", artRevision: 1, artContentHash: "art",
    targetPlaythroughSeconds: 5, routeBudgetHash: "budget", sectionBindings: [{ sectionId: "opening", episode: 1 }],
    routeOnlySectionIds: ["choice"], completeRouteSectionIds: [["opening", "choice"]],
  };
  const script = { episodes: [{ ep: 1, scenes: [{ sceneId: "S01", characters: [], flow: [{ action: "Opening action." }] }] }] };
  const state: ScriptReviewState = {
    status: status === "ready" ? "candidate_ready" : "prepared", staleReasons: [],
    acceptedReviewState: { ...evidence, staleReasons: [...evidence.staleReasons] },
    acceptedScript: { ...identity, binding, script },
    candidate: { ...baseCandidate, status, expectedScriptRevision: 1, binding, script: status === "ready" ? script : null },
  };
  vi.spyOn(plotloomApi, "getScript").mockResolvedValue(state);
  const reopen = vi.spyOn(plotloomApi, "reopenScript");
  await act(async () => root.render(createElement(ScriptPanel, { projectId: "project", readOnly: false, contextSectionId: sectionId })));
  expect(host.textContent).toContain("查看保留的已确认剧本");
  expect(host.textContent).not.toContain("查看当前已确认剧本");
  expect(host.textContent).not.toContain("当前已确认剧本 r1");
  expect(host.textContent).toContain("保留的已确认剧本 r1");
  if (sectionId === "choice") expect(host.textContent).toContain("将此节点作为路线控制");
  else expect(host.querySelector('[aria-label="当前节点的剧本场次"]')?.textContent).toContain("Opening action.");
  expect(host.querySelector('[aria-label="保留的已确认内容"]')?.textContent).toContain("美术设定版本已变化");
  const button = [...host.querySelectorAll("button")].find(b => b.textContent === "重新打开剧本")!;
  expect(button.disabled).toBe(true);
  await act(async () => button.click());
  expect(reopen).not.toHaveBeenCalled();
  if (status === "ready") expect([...host.querySelectorAll("button")].find(b => b.textContent === "确认使用此剧本")?.disabled).toBe(false);
});

it.each(["prepared", "ready"] as const)("fresh %s Art candidate cannot reopen retained accepted evidence", async status => {
  const binding = {} as ArtBinding;
  const state: ArtReviewState = {
    status: status === "ready" ? "candidate_ready" : "prepared", staleReasons: [],
    acceptedReviewState: { ...evidence, staleReasons: [...evidence.staleReasons] },
    acceptedArt: { ...identity, binding, art: { scenes: [], props: [] } },
    candidate: { ...baseCandidate, status, expectedArtRevision: 1, binding: { ...binding, sectionIds: [] }, art: status === "ready" ? { scenes: [], props: [] } : null },
  };
  vi.spyOn(plotloomApi, "getArt").mockResolvedValue(state);
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ decisions: [], states: [] });
  const reopen = vi.spyOn(plotloomApi, "reopenArt");
  await act(async () => root.render(createElement(ArtPanel, { projectId: "project", readOnly: false })));
  const button = [...host.querySelectorAll("button")].find(b => b.textContent === "重新打开美术提案")!;
  expect(button.disabled).toBe(true);
  expect(host.querySelector('[aria-label="保留的已确认内容"]')?.textContent).toContain("美术设定版本已变化");
  await act(async () => button.click());
  expect(reopen).not.toHaveBeenCalled();
  if (status === "ready") expect([...host.querySelectorAll("button")].find(b => b.textContent === "确认使用此美术提案")?.disabled).toBe(false);
});

it("keeps retained Storyboard evidence distinct while a fresh candidate is ready", async () => {
  const binding = { scriptRevision: 1 } as StoryboardReviewBinding;
  const state: StoryboardReviewState = {
    status: "candidate_ready", staleReasons: [],
    acceptedReviewState: { ...evidence, staleReasons: [...evidence.staleReasons] },
    acceptedReview: { ...identity, binding, storyboard: { episodes: [] } },
    candidate: { ...baseCandidate, status: "ready", expectedReviewRevision: 1, binding, storyboard: { episodes: [] } },
  };
  vi.spyOn(plotloomApi, "getStoryboardSourceReview").mockResolvedValue(state);
  await act(async () => root.render(createElement(StoryboardReviewPanel, { projectId: "project", readOnly: false, onInstalled: vi.fn(async () => undefined) })));
  expect(host.textContent).toContain("查看保留的已确认分镜");
  expect(host.textContent).not.toContain("查看当前已确认分镜");
  expect([...host.querySelectorAll("button")].find(b => b.textContent === "production bridge")?.disabled).toBe(true);
  expect([...host.querySelectorAll("button")].find(b => b.textContent === "确认此分镜评审方案")?.disabled).toBe(false);
});
