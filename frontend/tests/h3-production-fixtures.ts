import type { H3ReviewedDirections, VideoJobPrepareBody } from "../src/api";
import type { Batch, Target } from "../src/features/video-batch/contracts";

export const batchId = "10000000-0000-4000-8000-000000000001";
export const sourceHash = "a".repeat(64), manifestHash = "b".repeat(64), briefHash = "c".repeat(64);
export function productionTarget(request: VideoJobPrepareBody): Target {
  return { shotId: request.shotId, title: "守灯人的选择", mode: "generate", jobId: null, sourceHash,
    args: { seed: request.seed!, profile_id: request.profileId!, aspect_policy: request.aspectPolicy! },
    sources: [{ path: "shot.action", label: "动作", text: "守灯人把保险丝放回原处。" }],
    directions: null, compiledPrompt: null, authoredDurationUnits: 3000, requestedSeconds: 15, requestedFrames: 362, selectionRevision: 1,
    productionBrief: { version: "plotloom.production-brief.v2", displayVersion: "plotloom.production-brief-display.v2", contentLocale: "zh-CN", sourceHash, briefHash,
      sections: ["shot", "context", "presentation", "references", "timing", "settings"].map(id => ({ id, label: ({ shot: "画面、动作与连续性", context: "人物与对白原文", presentation: "画面文字与呈现方式", references: "已审阅参考素材", timing: "时长与播放窗口", settings: "生成设置与可见效果" } as Record<string, string>)[id], content: {}, items: [{ path: `${id}.meaning`, label: "创作要求", value: "守灯人把保险丝放回原处，不新增对白。" }] })),
      adapterConstraints: ["不得新增对白或画面文字。"], discretion: "仅可忠实调整表述。", conflicts: [] },
  };
}
export function productionBatch(request: VideoJobPrepareBody): Batch {
  return { id: batchId, projectId: "project", revision: 1, controlRevision: 0, state: "setup", manifestHash,
    manifest: { scopeShotIds: [request.shotId], kept: [], blockers: [], targets: [productionTarget(request)],
      setup: { profileId: request.profileId!, aspectPolicy: request.aspectPolicy!, maxJobs: null, maxRequestedSeconds: null, shotIds: [request.shotId], singleRequest: request }, newJobs: 1, requestedSeconds: 15 },
    execution: { jobs: {}, segments: {} },
  };
}
export function readyProductionBatch(request: VideoJobPrepareBody): Batch {
  const batch = productionBatch(request), target = batch.manifest.targets[0];
  batch.state = "ready"; batch.revision = 3;
  target.directions = { sourceHash, fields: [{ path: "shot.action", english: "The keeper puts the fuse back. Add no speech." }],
    fidelityCheck: { version: "assistant-fidelity.v1", batchId, attemptId: "20000000-0000-4000-8000-000000000001", resultHash: "d".repeat(64) } };
  target.compiledPrompt = "Exact compiled provider prompt. Add no speech.";
  target.fidelity = { verdict: "pass", checkedPaths: ["shot.action"], checkedDimensions: ["actions", "identities", "positions", "sound_roles", "negation", "completeness", "exact_text", "creative_discretion"], findings: [] };
  return batch;
}
export function authorizeProductionBatch(batch: Batch): Batch {
  const target = batch.manifest.targets[0];
  const packageValue: H3ReviewedDirections = { sourceHash: target.sourceHash, fields: target.directions!.fields,
    fidelityCheck: target.directions!.fidelityCheck!, intentAuthorization: { version: "production-intent.v2", briefHash },
    promptSha256: "e".repeat(64), reviewBasis: { version: "production-intent.v2", batchId: batch.id, manifestHash: batch.manifestHash, shotId: target.shotId } };
  return { ...batch, state: "running", revision: batch.revision + 1,
    execution: { ...batch.execution, authorizedManifestHash: batch.manifestHash, intentReviewVersion: "production-intent.v2" },
    authorizedDirections: { [target.shotId]: packageValue } };
}
