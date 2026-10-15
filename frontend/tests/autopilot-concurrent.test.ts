import { expect, it } from "vitest";
import { activityLabel } from "../src/features/autopilot/ConcurrentActivity";
import { projectAutopilotProgress } from "../src/features/autopilot/progress";
import { fixtureRun } from "./autopilot-fixture";
import type { AutopilotActivity } from "../src/features/autopilot/contracts";

const activity = (state: AutopilotActivity["state"], id = state): AutopilotActivity => ({
  operationKey: `character-reference:${id}`, owner: "character-reference", subjectId: id,
  jobId: `job-${id}`, domain: "image", state,
});

it("counts retained unique image bytes before complete discovery without inventing a total", () => {
  const progress = projectAutopilotProgress({ ...fixtureRun, bundle: null, checkpoints: [
    { operationKey: "character-reference:c1", state: "delivered", evidence: { owner: "character-reference", result: { candidateAssetIds: ["asset1", "asset2"] } } },
    { operationKey: "image:s1", state: "delivered", evidence: { owner: "image", result: { candidateAssetIds: ["asset2"] } } },
  ], activities: [activity("generating"), activity("validating"), activity("queued"), activity("unknown")] });
  expect(progress).toMatchObject({ imagesRetained: 2, imagesRequired: null, imagesSelected: 0, generating: 1, validating: 1, queued: 1 });
  expect(progress.activities).toHaveLength(4);
});

it("retains candidate counts while invalidating current selections after manual takeover", () => {
  const run = { ...fixtureRun, state: "taken_over" as const, materialCurrent: false,
    bundle: { inventory: { subjects: [{ owner: "character-reference", id: "c1" }] }, frames: [], references: [] },
    checkpoints: [{ operationKey: "character-reference:c1", state: "adopted", evidence: { owner: "character-reference", result: { candidateAssetIds: ["asset1"] } } }] };
  expect(projectAutopilotProgress(run)).toMatchObject({ imagesSelected: 0, imagesRetained: 1 });
});

it("describes paused queues and unresolved outcomes without asserting process completion", () => {
  expect(activityLabel(activity("queued"), { ...fixtureRun, state: "paused" })).toBe("已暂停，保留原任务");
  expect(activityLabel(activity("unknown"), { ...fixtureRun, state: "cancelled" })).toBe("结果待核对");
  expect(activityLabel(activity("generating"), { ...fixtureRun, state: "cancelled" })).toBe("正在生成");
});
