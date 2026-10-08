import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { demoProject } from "../src/demo";
import { CreatorProductionInspector } from "../src/features/graph/CreatorProductionInspector";
import type { AcceptedScriptRevision, ProductionBridgeState, StoryboardReview } from "../src/types";
import { bridgeState, installedProduction, replacementTarget } from "./production-bridge-fixture";

vi.mock("../src/features/graph/GraphWorkbenchContext", () => ({ useGraphWorkbench: () => ({ selectedNodeId: "opening" }) }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const cut = { sectionId: "opening", episode: 1, sceneIndex: 1, shotId: "installed-cut", cutIndex: 1, seconds: 5, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } };
const scenes = [{ sectionId: "opening", episode: 1, sceneIndex: 1, sceneId: "installed-scene", title: "S01", cutCount: 1 }];
const inputs = { scriptRevision: 2, scriptContentHash: "current-script" };
const script = { revision: 2, contentHash: "current-script", binding: { sectionBindings: [{ sectionId: "opening", episode: 1 }], routeOnlySectionIds: [] }, script: { episodes: [{ ep: 1, scenes: [{ sceneId: "S01", characters: [], flow: [{ action: "The light holds." }] }] }] } } as unknown as AcceptedScriptRevision;

function state(): ProductionBridgeState {
  return bridgeState({ status: "ready", installation: installedProduction({ inputs, scenes, cuts: [cut] }), proposal: {
    replacementTarget: replacementTarget(), revision: 3, contentHash: "c".repeat(64),
    inputs: { scriptRevision: 99, scriptContentHash: "candidate-only" }, scenes: [], cuts: [],
    presentation: { version: 1, reviewed: false, sourceHash: "f".repeat(64), sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} },
    intentPackage: { suggestionOrigin: "none", reviewState: "pending", entries: [] },
    conflicts: [], advisories: [], installable: false, preparedAt: "2026-10-08T00:00:00Z",
  } });
}

it.each(["current", "outdated"] as const)("uses installed source identity, not new proposal fields: %s", async status => {
  const host = document.createElement("div"), root = createRoot(host), bridge = state();
  bridge.installation!.status = status;
  const onOpenShot = vi.fn();
  const project = { ...demoProject, id: "project", stageRevisions: { ...demoProject.stageRevisions, storyboard: 1 }, storyboard: { ...demoProject.storyboard, shots: [{ ...demoProject.storyboard.shots[0], id: cut.shotId, sceneId: "installed-scene", durationUnits: 5000 }] } };
  try {
    await act(async () => root.render(createElement(CreatorProductionInspector, {
      project, graphCurrent: true, disabled: false, onNavigate: vi.fn(), onOpenShot,
      read: { retry: vi.fn(), data: { identity: "current", bridge, script: { candidate: null, acceptedScript: script, status: "accepted", staleReasons: [] }, review: { head: { revision: 1, status: "ready" }, activeApproval: { subjectRevision: 1 } } as StoryboardReview, errors: [] } },
    })));
    expect(host.textContent).not.toContain("剧本版本已变化");
    expect(host.querySelector("[data-production-shot='installed-cut']")).not.toBeNull();
    const button = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "镜头审核与媒体")!;
    expect(button.disabled).toBe(status === "outdated");
    await act(async () => button.click());
    if (status === "current") expect(onOpenShot).toHaveBeenCalledExactlyOnceWith("installed-cut");
    else { expect(onOpenShot).not.toHaveBeenCalled(); expect(host.textContent).toContain("需要重建"); }
  } finally { await act(async () => root.unmount()); }
});
