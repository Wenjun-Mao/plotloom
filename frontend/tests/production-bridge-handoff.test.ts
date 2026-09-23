import { expect, it } from "vitest";
import { bridgeCut, currentBridgeCut } from "../src/production-bridge-handoff";
import type { ProductionBridgeState } from "../src/types";

const cut = { shotId: "dock-s1-c8", sectionId: "dock", episode: 3, sceneIndex: 1, seconds: 8, source: { segmentIndex: 4, segmentSceneIndex: 1, cutIndex: 2 } };
const accepted: ProductionBridgeState = {
  status: "accepted", staleReasons: [], installedStageRevisions: { storyboard: 1 }, installedStoryboardCurrent: true,
  proposal: { revision: 2, contentHash: "a".repeat(64), inputs: {}, scenes: [], cuts: [cut], conflicts: [], advisories: [], installable: true, preparedAt: "2026-09-23T00:00:00Z", intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] } },
};

it("keeps exact F5 coordinates and duration only for a current installed head", () => {
  expect(bridgeCut(cut)).toEqual({ shotId: "dock-s1-c8", sectionId: "dock", episode: 3, sceneIndex: 1, seconds: 8, segmentIndex: 4, segmentSceneIndex: 1, sourceCutIndex: 2 });
  expect(currentBridgeCut(accepted, 1, "dock-s1-c8")?.seconds).toBe(8);
  expect(currentBridgeCut(accepted, 2, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut({ ...accepted, installedStoryboardCurrent: false }, 1, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut({ ...accepted, status: "stale" }, 1, "dock-s1-c8")).toBeUndefined();
  expect(currentBridgeCut(accepted, 1, "unknown")).toBeUndefined();
  expect(bridgeCut({ ...cut, source: { segmentIndex: 4, cutIndex: 2 } })).toBeUndefined();
});
