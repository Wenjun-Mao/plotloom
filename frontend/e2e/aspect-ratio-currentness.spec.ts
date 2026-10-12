import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { demoProject } from "../src/demo";
import { freezeReviewedFixtureDirections } from "./video_backends/minimax_h3/review-directions";
import { expect, test } from "./fixture";
import { createScriptProject, endpoint, fixture, json, writeDelivery } from "./f5a-fixture";
import { openMediaKeyframes, openMediaPreparation } from "./workbench-controls";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const reviewedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");

test("a saved aspect-ratio change withdraws dependent review and clip eligibility without altering retained bytes", async ({ page, request, workbench }, info) => {
  test.setTimeout(240_000);
  const projectId = await createFixtureProject(request, workbench.apiOrigin);
  const root = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;

  // Accept the upstream storyboard review from a deterministic checked-in
  // fixture. The canonical shot stage is separately installed through its
  // public stage API after the source map has admitted the graph.
  const storyboardReviewUrl = endpoint(workbench.apiOrigin, projectId);
  const reviewCandidate = await json(request.post(`${storyboardReviewUrl}/candidates`));
  await writeDelivery(reviewCandidate);
  await json(request.post(`${storyboardReviewUrl}/candidates/${reviewCandidate.jobId}/refresh`));
  await json(request.post(`${storyboardReviewUrl}/accept`, { data: {
    jobId: reviewCandidate.jobId,
    expectedReviewRevision: reviewCandidate.expectedReviewRevision,
    binding: reviewCandidate.binding,
  } }));

  const shotId = "shot_01";
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3A${shotId}`);
  const guide = page.getByTestId("recommended-workflow");
  await expect(guide).toContainText("前往分镜审核");
  await openMediaPreparation(page);
  await openMediaKeyframes(page);
  await page.getByLabel("审核人标签").fill("aspect-ratio fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜", exact: true }).click();
  await expect(guide).toContainText("当前镜头缺少可用的审核关键帧");
  await page.getByLabel("来源声明").fill("Aspect-ratio currentness fixture; reviewed local still.");
  await page.getByTestId("managed-image-upload").setInputFiles(reviewedStill);
  await page.getByTestId(/^keep-candidate-/).click();
  await page.getByTestId("visual-intent-source-refs").fill("Local synthetic fixture source.");
  await page.getByTestId("save-visual-intent").click();
  await page.getByLabel("审核兼容性说明").fill("Current selected shot keyframe for the bounded probe.");
  const keyframePost = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/reviewed-keyframes`);
  await page.getByTestId("select-reviewed-keyframe").click();
  const keyframeResponse = await keyframePost;
  expect(keyframeResponse.ok(), await keyframeResponse.text()).toBeTruthy();
  const { assetId } = await keyframeResponse.json() as { assetId: string };

  const visual = await json<{ characterReferences: { states: Array<{ characterId: string; revision: number }> } }>(
    request.get(`${root}/visual-workbench`),
  );
  for (const characterId of demoProject.storyboard.shots[0].characterIds) {
    const reference = await request.post(`${root}/character-references`, { data: {
      characterId,
      authority: "story_bible",
      primaryAssetId: assetId,
      complementaryAssetIds: [],
      expectedReferenceRevision: visual.characterReferences.states.find(state => state.characterId === characterId)?.revision ?? 0,
      reviewer: "aspect-ratio fixture reviewer",
      notes: "Explicit local fixture reference; not a creative acceptance claim.",
    } });
    expect(reference.ok(), await reference.text()).toBeTruthy();
  }

  const panel = page.getByTestId("video-pilot-panel");
  await panel.locator("details.video-production > summary").click();
  await panel.getByLabel("允许黑边画布（完整保留已审核图）").check();
  await panel.getByLabel("H3 时长（已审核）").selectOption("8");
  await freezeReviewedFixtureDirections(panel, "20261011");
  await panel.getByRole("button", { name: "提交一次" }).click();
  const reconcileResponse = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname.startsWith(`/api/v2/projects/${projectId}/video-jobs/`)
    && new URL(response.url()).pathname.endsWith("/reconcile"));
  await panel.getByRole("button", { name: "获取结果" }).click();
  const reconciled = await json<{ id: string; state: string; error: string | null }>(await reconcileResponse);
  expect(reconciled).toMatchObject({ state: "ingested", error: null });
  const segmentReview = panel.getByTestId(`video-segment-review-${reconciled.id}`);
  const frameInput = segmentReview.getByRole("spinbutton", { name: "片段入点（帧）", exact: true });
  await frameInput.fill("24");
  await segmentReview.getByRole("button", { name: "准备播放片段" }).click();
  const preview = segmentReview.locator('video[data-testid^="video-segment-preview-"]');
  await expect(preview).toBeVisible();
  await expect.poll(() => preview.evaluate(video => (video as HTMLVideoElement).duration)).toBeGreaterThan(0);
  await segmentReview.getByRole("button", { name: "确认用于故事" }).click();
  await expect(segmentReview.getByText("已选择片段 · 正用于故事", { exact: false })).toBeVisible();

  const baseline = await currentnessSnapshot(request, root, projectId, reconciled.id);
  expect(baseline.project.aspectRatio).toBe("9:16");
  expect(baseline.source.sectionMapStatus).toBe("current");
  expect(baseline.source.graphAdmissionStatus).toBe("current");
  expect(baseline.cast.status).toBe("accepted");
  expect(baseline.cast.acceptedReviewStatus).toBe("current");
  expect(baseline.art.status).toBe("accepted");
  expect(baseline.art.acceptedReviewStatus).toBe("current");
  expect(baseline.script.status).toBe("accepted");
  expect(baseline.script.acceptedReviewStatus).toBe("current");
  expect(baseline.storyboardSourceReview.status).toBe("accepted");
  expect(baseline.storyboardSourceReview.acceptedReviewStatus).toBe("current");
  expect(baseline.canonicalStages.every((stage: { status: string }) => stage.status === "ready")).toBe(true);
  expect(baseline.shotReview.activeApproval).not.toBeNull();
  expect(baseline.videoJob).toMatchObject({ state: "ingested", inputStatus: "current", productionEligible: true, current: true, selected: true });
  expect(baseline.videoJob.playbackSegment).toMatchObject({ current: true, previewEligible: true, selected: true });
  const originalVideoHash = baseline.videoJob.outputHash;
  const originalSegmentHash = baseline.videoJob.playbackSegment.derivativeHash;
  const originalVideoBytes = await readBytes(request, `${root}/video-jobs/${reconciled.id}/media`);
  const originalSegmentBytes = await readBytes(request, `${root}/video-segments/${baseline.videoJob.playbackSegment.id}/preview`);
  expect(sha256(originalVideoBytes)).toBe(originalVideoHash);
  expect(sha256(originalSegmentBytes)).toBe(originalSegmentHash);
  expect((await request.get(`${root}/video-jobs/${reconciled.id}/playback`)).ok()).toBe(true);
  await info.attach("aspect-ratio-baseline.json", { body: Buffer.from(JSON.stringify(baseline, null, 2)), contentType: "application/json" });

  const mutations: string[] = [];
  const recordMutation = (pending: import("@playwright/test").Request) => {
    if (new URL(pending.url()).pathname.startsWith("/api/v2/") && ["POST", "PUT", "PATCH", "DELETE"].includes(pending.method())) {
      mutations.push(`${pending.method()} ${new URL(pending.url()).pathname}`);
    }
  };
  page.context().on("request", recordMutation);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await page.getByLabel("画幅", { exact: true }).selectOption("16:9");
  const saveResponse = page.waitForResponse(response => response.request().method() === "PATCH"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}`);
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  expect((await saveResponse).ok()).toBe(true);
  await expect(page.getByLabel("画幅", { exact: true })).toHaveValue("16:9");

  const after = await currentnessSnapshot(request, root, projectId, reconciled.id);
  expect(after.project.aspectRatio).toBe("16:9");
  expect(after.source.sectionMapStatus).toBe("current");
  expect(after.source.graphAdmissionStatus).toBe("stale");
  expect(after.source.acceptedSectionMapHash).toBe(baseline.source.acceptedSectionMapHash);
  expect(after.cast.status).toBe("stale");
  expect(after.art.status).toBe("stale");
  expect(after.script.status).toBe("stale");
  expect(after.storyboardSourceReview.status).toBe("stale");
  expect(after.canonicalStages.length).toBe(baseline.canonicalStages.length);
  expect(after.canonicalStages.every((stage: { status: string }) => stage.status === "stale")).toBe(true);
  expect(after.shotReview.activeApproval).toBeNull();
  expect(after.shotReview.decisions).toHaveLength(baseline.shotReview.decisions.length);
  expect(after.videoJob).toMatchObject({ state: "ingested", inputStatus: "stale", productionEligible: false, current: false, selected: false });
  expect(after.videoJob.playbackSegment).toBeNull();
  expect(after.videoJob.segments[0]).toMatchObject({ current: false, previewEligible: true, selected: false });
  expect(after.videoJob.outputHash).toBe(originalVideoHash);
  expect(after.videoJob.segments[0].derivativeHash).toBe(originalSegmentHash);
  expect(sha256(await readBytes(request, `${root}/video-jobs/${reconciled.id}/media`))).toBe(originalVideoHash);
  expect(sha256(await readBytes(request, `${root}/video-segments/${baseline.videoJob.playbackSegment.id}/preview`))).toBe(originalSegmentHash);
  expect((await request.get(`${root}/video-jobs/${reconciled.id}/playback`)).status()).toBe(404);
  expect(mutations).toContain(`PATCH /api/v2/projects/${projectId}`);
  expect(mutations.some(item => /video-jobs|video-segments|reviewed-keyframes|storyboard-review|\/accept/.test(item))).toBe(false);

  // Re-entry preserves the same stale/current split; the Brief write does not
  // silently rebuild stages, replay selection, or restore playback.
  await page.reload();
  await expect(page.getByLabel("画幅", { exact: true })).toHaveValue("16:9");
  const afterReload = await currentnessSnapshot(request, root, projectId, reconciled.id);
  expect(afterReload.source.graphAdmissionStatus).toBe("stale");
  expect(afterReload.cast.status).toBe("stale");
  expect(afterReload.art.status).toBe("stale");
  expect(afterReload.script.status).toBe("stale");
  expect(afterReload.storyboardSourceReview.status).toBe("stale");
  expect(afterReload.videoJob).toMatchObject({ state: "ingested", inputStatus: "stale", current: false, selected: false });
  expect(sha256(await readBytes(request, `${root}/video-jobs/${reconciled.id}/media`))).toBe(originalVideoHash);

  const recoveryGuidance: Record<string, { text: string; controls: Array<{ name: string; disabled: boolean }> }> = {};
  const inspect = async (key: string, url: string, testId: string, readyText: string) => {
    await page.goto(url);
    const panel = page.getByTestId(testId);
    await expect(panel).toBeVisible();
    await expect(panel).toContainText(readyText);
    const controls = await panel.getByRole("button").evaluateAll(buttons => buttons.map(button => ({
      name: (button as HTMLButtonElement).innerText.trim(),
      disabled: (button as HTMLButtonElement).disabled,
    })));
    recoveryGuidance[key] = { text: await panel.innerText(), controls };
    return panel;
  };
  const sourceMap = await inspect("sourceMap", `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#section-map`, "section-map", "当前 r1");
  await expect(sourceMap).toContainText("当前 r1");
  await expect(sourceMap).toContainText("需要重新检查");
  const sourceWorkflowGuide = page.getByTestId("recommended-workflow");
  await expect(sourceWorkflowGuide).toContainText("下一步点击本页「应用到故事路线」");
  recoveryGuidance.sourceWorkflow = { text: await sourceWorkflowGuide.innerText(), controls: [] };
  await expect(sourceMap.getByRole("button", { name: "应用到故事路线", exact: true })).toBeEnabled();

  const scriptPanel = await inspect("script", `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#script`, "script-review", "上下文已过期");
  await expect(scriptPanel).toContainText("上下文已过期");
  await expect(scriptPanel.getByRole("button", { name: "准备剧本任务", exact: true })).toBeEnabled();
  await expect(scriptPanel).toContainText("美术设定尚未确认");
  await expect(scriptPanel.getByRole("link", { name: "在新页打开美术参考", exact: true })).toBeVisible();
  await expect(page.getByTestId("recommended-workflow")).toContainText("依据已变化");
  recoveryGuidance.scriptWorkflow = { text: await page.getByTestId("recommended-workflow").innerText(), controls: [] };
  for (const size of [{ width: 1280, height: 460 }, { width: 1280, height: 768 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await scriptPanel.evaluate(element => element.scrollIntoView({ block: "start" }));
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    if (process.env.PLOTLOOM_E2E_SCREENSHOT_DIR) {
      const screenshotPath = path.join(process.env.PLOTLOOM_E2E_SCREENSHOT_DIR, `aspect-script-stale-${size.width}x${size.height}.png`);
      await mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath });
    }
  }

  const storyboardReview = await inspect("storyboardReview", `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#storyboard-review`, "storyboard-review", "上下文已过期");
  await expect(storyboardReview).toContainText("上下文已过期");
  await expect(storyboardReview).toContainText("请先到“剧本”检查并确认当前内容，再回来继续。");
  await expect(storyboardReview.getByRole("link", { name: "在新页打开剧本", exact: true })).toBeVisible();
  await expect(storyboardReview.getByRole("button", { name: "准备分镜任务", exact: true })).toBeEnabled();

  await inspect("shotMedia", `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard&entity=shot%3A${shotId}`, "video-pilot-panel", "原片 → 调整片段 → 预览 → 用于故事");
  expect(recoveryGuidance.shotMedia.text.length).toBeGreaterThan(0);

  const exactBriefWrites = [`PATCH /api/v2/projects/${projectId}`, `PUT /api/v2/projects/${projectId}/authoring-drafts`].sort();
  expect([...mutations].sort()).toEqual(exactBriefWrites);
  const evidence = { projectId, videoJobId: reconciled.id, aspectRatio: { from: "9:16", to: "16:9" }, baseline, after, afterReload, mutations, recoveryGuidance, bytes: { videoSha256: originalVideoHash, selectedSegmentSha256: originalSegmentHash } };
  await info.attach("aspect-ratio-currentness-evidence.json", { body: Buffer.from(JSON.stringify(evidence, null, 2)), contentType: "application/json" });
  if (process.env.PLOTLOOM_E2E_RETAIN_PARENT) {
    const evidenceDirectory = path.join(path.dirname(workbench.outputsRoot), "evidence");
    await mkdir(evidenceDirectory, { recursive: true });
    await writeFile(path.join(evidenceDirectory, "aspect-ratio-currentness.json"), JSON.stringify(evidence, null, 2));
  }

  const evidenceSummary = {
    projectId,
    videoJobId: reconciled.id,
    aspect: "9:16->16:9",
    writes: mutations,
    states: {
      sectionMap: after.source.sectionMapStatus,
      graphAdmission: after.source.graphAdmissionStatus,
      cast: after.cast.status,
      art: after.art.status,
      script: after.script.status,
      storyboardReview: after.storyboardSourceReview.status,
      canonicalStages: after.canonicalStages.map((stage: { status: string }) => stage.status),
      video: [after.videoJob.state, after.videoJob.inputStatus, after.videoJob.productionEligible, after.videoJob.current, after.videoJob.selected],
      segment: after.videoJob.segments[0] && [after.videoJob.segments[0].previewEligible, after.videoJob.segments[0].current, after.videoJob.segments[0].selected],
      recovery: Object.fromEntries(Object.entries(recoveryGuidance).map(([key, value]) => [key, value.controls.filter(control => /恢复|准备/.test(control.name))])),
    },
  };
  console.info(`ASPECT_RATIO_EVIDENCE ${JSON.stringify(evidenceSummary)}`);
});

async function createFixtureProject(request: Parameters<typeof createScriptProject>[0], origin: string): Promise<string> {
  const storyBible = structuredClone(demoProject.storyBible);
  const projectId = await createScriptProject(request, origin, "aspect-ratio-currentness-20261011", {}, ["cast", "art", "script"], {
    briefOverrides: { aspectRatio: "9:16" },
    initialStages: [{ stage: "story_bible", payload: storyBible }],
  });
  const root = `${origin}/api/v2/projects/${projectId}`;
  const sceneBeats = structuredClone(demoProject.sceneBeats) as any;
  const sceneNodeById: Record<string, string> = {
    scene_arrival: "opening",
    scene_ending_city: "beacon",
    scene_ending_brother: "dock",
  };
  const keptSceneIds = new Set(Object.keys(sceneNodeById));
  sceneBeats.scenes = sceneBeats.scenes.filter((scene: { id: string }) => keptSceneIds.has(scene.id))
    .map((scene: { id: string; storyNodeId: string }) => ({ ...scene, storyNodeId: sceneNodeById[scene.id] }));
  const keptBeatIds = new Set(sceneBeats.scenes.flatMap((scene: { beatIds: string[] }) => scene.beatIds));
  sceneBeats.beats = sceneBeats.beats.filter((beat: { id: string }) => keptBeatIds.has(beat.id));
  sceneBeats.dialogueCues = sceneBeats.dialogueCues.filter((cue: { beatId: string }) => keptBeatIds.has(cue.beatId));
  await patchStage(request, root, "scene_beats", sceneBeats);

  const storyboard = structuredClone(demoProject.storyboard) as any;
  storyboard.shots = storyboard.shots.filter((shot: { sceneId: string }) => keptSceneIds.has(shot.sceneId));
  const keptShotIds = new Set(storyboard.shots.map((shot: { id: string }) => shot.id));
  storyboard.shotBeatLinks = storyboard.shotBeatLinks.filter((link: { shotId: string; beatId: string }) => keptShotIds.has(link.shotId) && keptBeatIds.has(link.beatId));
  await patchStage(request, root, "storyboard", storyboard);
  return projectId;
}

async function patchStage(request: Parameters<typeof createScriptProject>[0], root: string, stage: "scene_beats" | "storyboard", payload: unknown): Promise<void> {
  const state = await json<{ stages: Array<{ head: { stage: string; revision: number } }> }>(request.get(`${root}/stages`));
  const current = state.stages.find(item => item.head.stage === stage);
  if (!current) throw new Error(`Missing ${stage} stage head`);
  await json(request.patch(`${root}/stages/${stage}`, { data: { expectedRevision: current.head.revision, payload } }));
}

async function currentnessSnapshot(request: Parameters<typeof createScriptProject>[0], root: string, projectId: string, jobId: string): Promise<any> {
  const [project, source, cast, art, script, storyboardSourceReview, stages, shotReview, jobs] = await Promise.all([
    json(request.get(`${root}`)),
    json(request.get(`${root}/source-outline`)),
    json(request.get(`${root}/cast`)),
    json(request.get(`${root}/art`)),
    json(request.get(`${root}/script`)),
    json(request.get(`${root}/storyboard-source-review`)),
    json(request.get(`${root}/stages`)),
    json(request.get(`${root}/storyboard-review`)),
    json(request.get(`${root}/video-jobs`)),
  ]);
  const videoJob = jobs.jobs.find((item: { id: string }) => item.id === jobId);
  if (!videoJob) throw new Error(`Video job ${jobId} disappeared`);
  return {
    project: { revision: project.revision, aspectRatio: project.brief.aspectRatio },
    source: {
      sectionMapStatus: source.sectionMapStatus,
      sectionMapStaleReasons: source.sectionMapStaleReasons,
      acceptedSectionMapHash: source.acceptedSectionMap?.contentHash,
      graphAdmissionStatus: source.graphAdmission?.status,
      graphAdmissionReasons: source.graphAdmission?.staleReasons,
    },
    cast: { status: cast.status, acceptedReviewStatus: cast.acceptedReviewState.status, staleReasons: cast.staleReasons },
    art: { status: art.status, acceptedReviewStatus: art.acceptedReviewState.status, staleReasons: art.staleReasons },
    script: { status: script.status, acceptedReviewStatus: script.acceptedReviewState.status, staleReasons: script.staleReasons },
    storyboardSourceReview: { status: storyboardSourceReview.status, acceptedReviewStatus: storyboardSourceReview.acceptedReviewState.status, staleReasons: storyboardSourceReview.staleReasons },
    canonicalStages: stages.stages.map((item: { head: { stage: string; status: string; revision: number; staleReasons: string[] } }) => ({ stage: item.head.stage, status: item.head.status, revision: item.head.revision, staleReasons: item.head.staleReasons })),
    shotReview: { activeApproval: shotReview.activeApproval, decisions: shotReview.decisions },
    videoJob: {
      id: videoJob.id, state: videoJob.state, inputStatus: videoJob.inputStatus,
      productionEligible: videoJob.productionEligible, current: videoJob.current, selected: videoJob.selected,
      outputHash: videoJob.outputHash, playbackSegment: videoJob.playbackSegment, segments: videoJob.segments,
    },
  };
}

async function readBytes(request: Parameters<typeof createScriptProject>[0], url: string): Promise<Buffer> {
  const response = await request.get(url);
  expect(response.ok(), await response.text()).toBe(true);
  return response.body();
}

function sha256(content: Buffer): string {
  return createHash("sha256").update(content).digest("hex");
}
