import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { BriefPage } from "../src/pages/BriefPage";
import { demoProject } from "../src/demo";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import { briefStructureBasis } from "../src/features/graph/briefStructureBasis";
import { creatorStructure, canonicalStructure } from "../src/features/graph/creatorStructure";
import { graphActionProjection } from "../src/features/graph/graphActionProjection";
import { ProfessionalPresentationProvider, useProfessionalPresentation, type ProfessionalPresentation } from "../src/features/graph/ProfessionalPresentation";
import type { ProductionBridgeState, SourceOutlineReviewState, StoryGraph } from "../src/types";

const launch = vi.hoisted(() => vi.fn((_props: Record<string, unknown>) => null));
vi.mock("../src/features/autopilot/AutopilotWorkspace", () => ({ AutopilotLaunch: launch }));

const draft = graphDraftFixture();
const owner = () => graphControllerFixture({ draft: structuredClone(draft), state: { bindingHash: draft.bindingHash, baseCanonicalRevision: 1, draft: null, initialPayload: draft, readOnlyReason: null } });
const brief = { ...demoProject.brief, endingCount: 1, desiredJoinCount: 0, decisionPointsPerPath: 0 };
const canonical: StoryGraph = { startNodeId: "opening", nodes: draft.mapping.topology.nodes.map(node => ({ ...node, title: node.id, summary: "正文", footageMode: "footage" })), edges: draft.mapping.topology.edges.map(edge => ({ ...edge, sourceNodeId: edge.sourceNodeId!, targetNodeId: edge.targetNodeId!, choiceText: null })), joinContracts: [] };

it("keeps launch dirty and saved visual direction bound to canonical Brief after recovery", async () => {
  const root = createRoot(document.createElement("div"));
  const saved = { ...demoProject.brief, visualStyleSelections: [], visualStyle: "已保存风格" };
  const recovered = { ...saved, visualStyle: "尚未保存风格", nodeBudget: saved.nodeBudget + 1 };
  try {
    await act(async () => root.render(createElement(BriefPage, { value: recovered, savedValue: saved, hasSavedProject: true, saving: false, onSave: vi.fn() })));
    expect(launch.mock.calls.at(-1)?.[0]).toMatchObject({ dirty: true, visualDirection: "已保存风格" });
  } finally { await act(async () => root.unmount()); }
});

it("counts equivalent canonical and editable topology without creating authoring state", () => {
  expect(canonicalStructure(canonical, brief).actual).toEqual(creatorStructure(draft, brief).actual);
  const graph = owner();
  expect(briefStructureBasis(graph, canonical, brief).label).toBe("当前共享图草稿");
  graph.draft = null; graph.state!.readOnlyReason = "只读";
  expect(briefStructureBasis(graph, canonical, brief)).toMatchObject({ label: "当前已接受规范图", structure: { actual: { nodes: 2, endings: 1, routes: 1 } } });
  for (const status of ["loading", "failed"] as const) {
    graph.readStatus = status;
    expect(briefStructureBasis(graph, canonical, brief).structure).toBeNull();
  }
  graph.readStatus = "ready"; graph.stale = true;
  expect(briefStructureBasis(graph, canonical, brief).structure).toBeNull();
});

it("retains draft-only incompleteness and guards cyclic, detached and capped enumeration", () => {
  const graph = owner(); graph.draft!.fieldBuffers.unfinished = "{";
  expect(briefStructureBasis(graph, canonical, brief).structure?.incomplete).toBe(true);
  expect(canonicalStructure(canonical, brief).incomplete).toBe(false);
  const cyclic = structuredClone(canonical);
  cyclic.edges.push({ ...cyclic.edges[0], id: "cycle", sourceNodeId: "ending", targetNodeId: "opening" });
  expect(canonicalStructure(cyclic, brief).actual.routes).toBe(1);
  const detached = structuredClone(canonical); detached.edges = [];
  expect(canonicalStructure(detached, brief)).toMatchObject({ incomplete: true, actual: { detached: 1, routes: 0 } });
});

it("projects shared whole-graph prerequisites, uncertainty and currentness", () => {
  const graph = owner();
  const source = { source: { revision: 1 }, acceptedOutline: { sourceRevision: 1 }, outlineStatus: "accepted", acceptedSectionMap: { mapping: draft.mapping, revision: 1, contentHash: "accepted" }, sectionMapStatus: "current", graphAdmission: null } as unknown as SourceOutlineReviewState;
  const production = { identity: "current", bridge: {} as ProductionBridgeState, errors: [] };
  const project = (status: "ready" | "loading" | "failed", value: SourceOutlineReviewState | null = source) => graphActionProjection(graph, brief, false, { status, value }, production);
  expect(project("ready")).toMatchObject({ disabled: false, confirmDisabled: false, applyDisabled: false });
  for (const status of ["loading", "failed"] as const) expect(project(status)).toMatchObject({ confirmDisabled: true, applyDisabled: true, status: "来源与大纲尚未核实，请先重新读取。" });
  expect(project("ready", { ...source, acceptedOutline: null }).status).toContain("先保存来源并确认大纲");
  expect(project("ready", { ...source, outlineStatus: "reopened" })).toMatchObject({ disabled: false, confirmDisabled: true, applyDisabled: true, status: "大纲修订已打开，请先确认当前大纲。" });
  expect(project("ready", { ...source, source: { ...source.source!, revision: 2 } })).toMatchObject({ disabled: false, confirmDisabled: true, applyDisabled: true, status: "来源已变化，请先确认当前来源的大纲。" });
  expect(project("ready", { ...source, outlineStatus: "reopened", source: { ...source.source!, revision: 2 } }).status).toBe("来源已变化，请先确认当前来源的大纲。");
  graph.draft!.fieldBuffers.unfinished = "{";
  expect(project("ready")).toMatchObject({ confirmDisabled: true, applyDisabled: true });
  graph.draft!.fieldBuffers = {};
  expect(graphActionProjection(graph, brief, false, { status: "ready", value: source }, undefined)).toMatchObject({ confirmDisabled: true, applyDisabled: true, status: "投产状态尚未核对，暂不能应用路线。" });
  source.graphAdmission = { status: "current", graphRevision: 1, sectionMapRevision: 1, sectionMapContentHash: "accepted" } as SourceOutlineReviewState["graphAdmission"];
  expect(project("ready")).toMatchObject({ applyDisabled: true, status: "当前图内容已应用到故事路线。" });
});

it("retains only active-project Pro visuals through child unmount and resets on project/provider exit", async () => {
  const root = createRoot(document.createElement("div")); let presentation!: ProfessionalPresentation;
  function Probe() { presentation = useProfessionalPresentation(); return null; }
  const render = async (projectId: string, visible: boolean) => act(async () => root.render(createElement(ProfessionalPresentationProvider, { projectId, children: visible ? createElement(Probe) : null })));
  try {
    await render("a", true); const first = presentation;
    first.positions.opening = { x: 20, y: 30 }; first.viewport = { x: 10, y: 40, zoom: .8 };
    await render("a", false); await render("a", true); expect(presentation).toBe(first);
    await render("b", true); expect(presentation).toEqual({ positions: {} });
    // A late callback closes over the retired session object, never the new one.
    first.viewport = { x: 99, y: 99, zoom: 2 }; first.positions.late = { x: 99, y: 99 };
    expect(presentation).toEqual({ positions: {} });
    await render("a", true); expect(presentation).not.toBe(first); expect(presentation).toEqual({ positions: {} });
    await act(async () => root.render(null)); await render("a", true); expect(presentation).toEqual({ positions: {} });
  } finally { await act(async () => root.unmount()); }
});
