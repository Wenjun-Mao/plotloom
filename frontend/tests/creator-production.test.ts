import { expect, it } from "vitest";
import type { AcceptedScriptRevision, ProductionBridgeProposal, Shot, SourceOutlineReviewState } from "../src/types";
import { installedCutMatches, nodeProductionScenes } from "../src/features/graph/productionProjection";
import { creatorAdmission } from "../src/features/graph/creatorAdmission";
import { graphDraftFixture } from "./graph-workbench-fixture";

const scene = { sceneId: "S01", characters: [], flow: [{ action: "The light holds." }] };
const accepted = { revision: 2, contentHash: "script-hash", binding: { sectionBindings: [{ sectionId: "opening", episode: 7 }], routeOnlySectionIds: ["choice"] }, script: { episodes: [{ ep: 7, scenes: [scene, scene] }] } } as unknown as AcceptedScriptRevision;
const cut = (sceneIndex: number, order: number, segmentIndex = sceneIndex, sourceCutIndex = order) => ({ sectionId: "opening", episode: 7, sceneIndex, shotId: `bound-${sceneIndex}-${order}`, cutIndex: order, seconds: 2.5, source: { segmentIndex, segmentSceneIndex: sceneIndex, cutIndex: sourceCutIndex } });
const proposal = () => ({ inputs: { scriptRevision: 2, scriptContentHash: "script-hash" }, scenes: [{ sectionId: "opening", episode: 7, sceneIndex: 2, sceneId: "canonical-two", title: "S01", cutCount: 2 }, { sectionId: "opening", episode: 7, sceneIndex: 1, sceneId: "canonical-one", title: "S01", cutCount: 1 }], cuts: [cut(2, 2, 3, 1), cut(1, 1), cut(2, 1)] }) as unknown as ProductionBridgeProposal;

it("binds every repeated location occurrence by formal coordinates and preserves exact installed identities", () => {
  const result = nodeProductionScenes(proposal(), accepted, "opening");
  expect(result.map(value => [value.sceneIndex, value.sceneId, value.cuts.map(value => value.shotId)])).toEqual([[1, "canonical-one", ["bound-1-1"]], [2, "canonical-two", ["bound-2-1", "bound-2-2"]]]);
  expect(result[1].cuts[1]).toMatchObject({ segmentIndex: 3, sourceCutIndex: 1, seconds: 2.5 });
  const shot = { id: "bound-2-2", sceneId: "canonical-two", durationUnits: 2500 } as Shot;
  expect(installedCutMatches(result[1].cuts[1], "canonical-two", shot)).toBe(true);
  expect(installedCutMatches(result[1].cuts[1], "canonical-one", shot)).toBe(false);
  expect(installedCutMatches(result[1].cuts[1], "canonical-two", { ...shot, durationUnits: 3000 })).toBe(false);
  expect(nodeProductionScenes(proposal(), accepted, "choice")).toEqual([]);
});

it.each([
  (value: ProductionBridgeProposal) => { value.inputs.scriptRevision = 1; },
  (value: ProductionBridgeProposal) => { value.scenes[0].sceneIndex = 3; },
  (value: ProductionBridgeProposal) => { value.scenes[0].sceneId = "canonical-one"; },
  (value: ProductionBridgeProposal) => { value.scenes[0].title = "S02"; },
  (value: ProductionBridgeProposal) => { value.cuts[0].episode = 1; },
  (value: ProductionBridgeProposal) => { value.cuts[0].seconds = 0.0001; },
  (value: ProductionBridgeProposal) => { value.cuts[0].shotId = "bound-2-1"; },
  (value: ProductionBridgeProposal) => { value.cuts[0].source = value.cuts[2].source; },
  (value: ProductionBridgeProposal) => { value.cuts[0].cutIndex = 3; },
  (value: ProductionBridgeProposal) => { value.cuts.push(cut(3, 1)); },
])("refuses ambiguous, stale or malformed projection rather than inferring a shot", alter => {
  const value = proposal(); alter(value);
  expect(() => nodeProductionScenes(value, accepted, "opening")).toThrow();
});

it("does not hide a retained old production under a route-only binding", () => {
  const value = proposal(); value.scenes[0].sectionId = "choice";
  expect(() => nodeProductionScenes(value, accepted, "choice")).toThrow("旧投产映射");
});

it("checks semantic mapping and exact admission while preserving first-install-only guards", () => {
  const draft = graphDraftFixture();
  const { sections, ...rest } = draft.mapping;
  const source = { sectionMapStatus: "current", acceptedSectionMap: { revision: 4, contentHash: "map-hash", mapping: { sections: structuredClone(sections), ...rest } }, graphAdmission: { status: "current", graphRevision: 3, sectionMapRevision: 4, sectionMapContentHash: "map-hash" } } as SourceOutlineReviewState;
  expect(JSON.stringify(source.acceptedSectionMap!.mapping)).not.toBe(JSON.stringify(draft.mapping));
  expect(creatorAdmission(draft, source, 3, true)).toMatchObject({ graphCurrent: true, installBlocked: true, structureBlocked: false });
  expect(creatorAdmission(draft, source, 2, false).graphCurrent).toBe(false);
  source.graphAdmission!.sectionMapContentHash = "other";
  expect(creatorAdmission(draft, source, 3, false).graphCurrent).toBe(false);
  source.graphAdmission!.sectionMapContentHash = "map-hash";
  draft.mapping.sections[0].title += " revised prose";
  expect(creatorAdmission(draft, source, 3, true)).toMatchObject({ graphCurrent: false, structureBlocked: false, installBlocked: true });
  draft.mapping.sections[0].footageMode = "route_only";
  expect(creatorAdmission(draft, source, 3, true).structureBlocked).toBe(true);
  expect(creatorAdmission(draft, source, 3, undefined).installBlocked).toBe(true);
});
