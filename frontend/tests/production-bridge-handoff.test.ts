import { expect, it } from "vitest";
import { bridgeCut, currentBridgeCut } from "../src/production-bridge-handoff";
import type { ProductionBridgeState } from "../src/types";
import { bridgeState, installedProduction, replacementTarget } from "./production-bridge-fixture";

const cut = { shotId: "dock-s1-c8", sectionId: "dock", episode: 3, sceneIndex: 1, seconds: 8, source: { segmentIndex: 4, segmentSceneIndex: 1, cutIndex: 2 } };
const accepted: ProductionBridgeState = bridgeState({ status: "accepted", installation: installedProduction({ cuts: [cut] }),
  proposal: { replacementTarget: replacementTarget(), presentation: { version: 1, reviewed: true, sourceHash: "f".repeat(64), sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} }, revision: 2, contentHash: "a".repeat(64), inputs: {}, scenes: [], cuts: [cut], conflicts: [], advisories: [], installable: true, preparedAt: "2026-09-23T00:00:00Z", intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] } },
});

it("keeps exact F5 coordinates and duration only for a current installed head", () => {
  expect(bridgeCut(cut)).toEqual({ shotId: "dock-s1-c8", sectionId: "dock", episode: 3, sceneIndex: 1, seconds: 8, segmentIndex: 4, segmentSceneIndex: 1, sourceCutIndex: 2 });
  expect(currentBridgeCut(accepted, 1, "dock-s1-c8")?.seconds).toBe(8);
  expect(currentBridgeCut(accepted, 2, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut({ ...accepted, installation: installedProduction({ status: "outdated", cuts: [cut] }) }, 1, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut({ ...accepted, installation: null }, 1, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut(accepted, 1, "unknown")).toBeUndefined();
  expect(bridgeCut({ ...cut, source: { segmentIndex: 4, cutIndex: 2 } })).toBeUndefined();
});

it.each([2.5, 1.001, 0.001, 8])("keeps source coordinates for exact decimal %s-second cuts", (seconds) => {
  const fractional = { ...cut, seconds };
  expect(bridgeCut(fractional)?.seconds).toBe(seconds);
  expect(currentBridgeCut({ ...accepted, installation: installedProduction({ cuts: [fractional] }) }, 1, cut.shotId)?.sourceCutIndex).toBe(2);
});

it("a new candidate cannot replace or suppress an independently current installed cut", () => {
  const candidate = { ...accepted, status: "ready" as const, proposal: { ...accepted.proposal!, revision: 3, cuts: [{ ...cut, seconds: 5 }] } };
  expect(currentBridgeCut(candidate, 1, cut.shotId)?.seconds).toBe(8);
  expect(currentBridgeCut({ ...candidate, installation: installedProduction({ status: "outdated", cuts: [cut] }) }, 1, cut.shotId)).toBeUndefined();
  expect(currentBridgeCut({ ...candidate, installation: installedProduction({ cuts: [] }) }, 1, cut.shotId)).toBeUndefined();
});

it.each([1.0004, true, NaN, Infinity, 0, -1])("does not admit invalid source duration %s", (seconds) => {
  expect(bridgeCut({ ...cut, seconds })).toBeUndefined();
});

it.each([0, -1, 1.5, true, Infinity])("keeps coordinates positive integers for value %s", (value) => {
  expect(bridgeCut({ ...cut, episode: value })).toBeUndefined();
  expect(bridgeCut({ ...cut, source: { ...cut.source, segmentIndex: value } })).toBeUndefined();
});
