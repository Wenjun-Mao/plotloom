import type { AutopilotRun, ReviewMaterial } from "../src/features/autopilot/contracts";
import type { ScriptBinding } from "../src/types";
export const fixtureMaterial: ReviewMaterial = { runRevision: 12, bundleHash: "a".repeat(64), bundle: {
  inventory: { routeCount: 2 }, references: [
    { owner: "character-reference", subjectId: "hero", name: "守塔人", decisionId: "hero-ref", assetId: "hero-reference" },
    { owner: "art-reference", subjectId: "tower", name: "灯塔", decisionId: "tower-ref", assetId: "tower-reference" }],
  frames: [{ shotId: "shot-1", sceneId: "tower", title: "检查灯芯", sceneName: "灯塔内部", direction: "背影中景，动作清晰可见。", assetId: "frame-1", description: "守塔人伸手检查灯芯。", characterIds: ["hero"], origin: "machine_provisional" },
    { shotId: "shot-2", sceneId: "tower", title: "灯光熄灭", sceneName: "灯塔内部", direction: "空环境全景，保留灯光与窗口关系。", assetId: "frame-2", description: "空灯塔里的灯光熄灭。", characterIds: [], origin: "machine_provisional" }],
  story: { characters: { hero: "守塔人" }, graph: { nodes: [{ id: "start", title: "灯塔", summary: "暴风雨迫近，守塔人必须决定灯塔的命运。" }, { id: "end-a", title: "点亮", summary: "灯光引导船只返回港口。" }, { id: "end-b", title: "熄灭", summary: "守塔人选择离开，海面恢复寂静。" }] },
    routes: [["start", "end-a"], ["start", "end-b"]], script: { episodes: [] }, scriptBinding: { sectionBindings: [], completeRouteSectionIds: [], routeOnlySectionIds: [] } as unknown as ScriptBinding, reports: [] }
} };
export const fixtureRun: AutopilotRun = { id: "disposable-run", projectId: "disposable", revision: 12, state: "awaiting_review", phase: "material-review", blocker: null,
  policy: { renderStyle: "live-action", artRenderStyle: "live-action", maxImages: 80, maxJobs: 96 }, checkpoints: [
    { operationKey: "characters", state: "adopted", evidence: { owner: "characters", result: { revision: 1, contentHash: "cast-hash" } } }],
  bundle: { inventory: { subjects: [{ owner: "character-reference" }, { owner: "art-reference" }] }, frames: [{}, {}], references: [{}, {}] }, handoff: null };
