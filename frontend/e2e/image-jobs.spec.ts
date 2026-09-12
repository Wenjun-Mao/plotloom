import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { demoProject } from "../src/demo";
import { expect, test } from "./fixture";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");
// Verification runs must not overwrite the reviewed, tracked evidence image.
const usabilityScreenshot = path.join(tmpdir(), "plotloom-p1-image-workflow-usability-1440x900.png");

type ImageJob = {
  id: string;
  parentCandidateAssetId: string | null;
  requestHash: string;
  request: { kind: "original" | "refinement" };
  deliveries: Array<{ state: string; candidates: Array<{ assetId: string; role: string }> }>;
};

test.describe("P1 self-contained copied image brief", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("prepares, copies, refreshes, refines, and invalidates a copied brief after an intent revision", async ({ page, request, workbench }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: async (value: string) => window.sessionStorage.setItem("copied-image-job", value) },
      });
    });
    const projectId = await createCanonicalProject(request, workbench.apiOrigin);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /05 分镜工作台/ }).click();
    await page.getByLabel("审核人标签").fill("P1 self-contained browser reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(page.getByText("当前批准：P1 self-contained browser reviewer", { exact: true })).toBeVisible();

    // P1.5 v3 jobs are reference-conditioned for visible characters. Create
    // that creator decision through the workbench before requesting a job;
    // the retained file is fixture evidence, not a generated pilot result.
    await page.getByLabel("来源声明").fill("Retained P0 fixture used as a P1.5 identity-reference regression input");
    await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
    const referenceAssetId = await page.getByTestId("reference-primary-asset").locator("option").nth(1).getAttribute("value");
    expect(referenceAssetId).toBeTruthy();
    await page.getByTestId("reference-primary-asset").selectOption(referenceAssetId!);
    await page.getByTestId("reference-reviewer").fill("P1.5 browser reference reviewer");
    await page.getByTestId("reference-notes").fill("Stable facial and build guidance only; pose, wardrobe, and lighting remain owned by each frozen shot.");
    await page.getByTestId("select-character-reference").click();
    await expect(page.getByTestId("character-reference-char_ruanxing")).toContainText("r1");

    const originalDirection = "Render the approved arrival shot with clear practical control-room lighting and readable facial detail.";
    const shotPicker = page.getByLabel("当前媒体镜头");
    const originalShotId = await shotPicker.inputValue();
    const alternateShotId = await shotPicker.locator("option").nth(1).getAttribute("value");
    await page.getByTestId("image-job-presentation-change").fill(originalDirection);
    await page.getByTestId("discard-image-job-direction").click();
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue("");
    await expect(page.getByTestId("discard-image-job-direction")).toHaveCount(0);
    await page.getByTestId("image-job-presentation-change").fill(originalDirection);
    if (alternateShotId && alternateShotId !== originalShotId) {
      await shotPicker.selectOption(alternateShotId);
      await expect(page.getByTestId("image-job-presentation-change")).toHaveValue("");
      await shotPicker.selectOption(originalShotId);
      await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(originalDirection);
    }
    await page.reload();
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(originalDirection);
    await page.evaluate(() => {
      const key = "plotloom:image-job-direction-drafts:v1";
      const drafts = JSON.parse(window.sessionStorage.getItem(key) || "{}");
      const first = Object.keys(drafts)[0];
      if (first) drafts[first].contextId = "obsolete-context";
      window.sessionStorage.setItem(key, JSON.stringify(drafts));
    });
    await page.reload();
    await expect(page.getByTestId("image-job-direction-stale")).toBeVisible();
    await page.getByRole("button", { name: "确认后恢复到当前上下文" }).click();
    await expect(page.getByTestId("image-job-direction-stale")).toHaveCount(0);
    const otherProjectId = await createCanonicalProject(request, workbench.apiOrigin);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${otherProjectId}&stage=storyboard`);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue("");
    await page.getByTestId("image-job-presentation-change").fill("This direction must remain isolated in the other project.");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(originalDirection);
    await prepareImageJob(page, projectId, "prepare-image-job");
    const original = await latestImageJob(request, workbench.apiOrigin, projectId);
    await expect(page.getByTestId(`image-job-${original.id}`)).toBeVisible();
    await copyImageJob(page, projectId, original.id);
    await expect(page.getByTestId("image-job-assignment")).toContainText("use built-in imagegen");
    await expect(page.getByTestId("image-job-copy-status")).toContainText("已复制到系统剪贴板");
    await expect.poll(() => page.evaluate(() => window.sessionStorage.getItem("copied-image-job"))).toContain("Codex image specialist assignment");
    await page.getByTestId(`refresh-image-job-${original.id}`).click();
    await expect(page.getByTestId(`image-job-${original.id}`)).toContainText("尚未收到 delivery");
    expect((await imageJob(request, workbench.apiOrigin, projectId, original.id)).deliveries).toEqual([]);
    await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined }));
    await copyImageJob(page, projectId, original.id);
    await expect(page.getByTestId("image-job-copy-status")).toContainText("手动复制");
    await page.getByTestId("select-image-job-assignment").click();

    const originalPackage = path.join(workbench.imageExchangeRoot, "jobs", original.id, "package");
    const originalRequest = await readJson(path.join(originalPackage, "request.json"));
    expect(originalRequest).toMatchObject({ schemaVersion: 3, packageVersion: 3, jobId: original.id });
    expect(originalRequest.references).toEqual(expect.arrayContaining([
      expect.objectContaining({ role: "character_identity:char_ruanxing" }),
    ]));
    expect(originalRequest.frozenSnapshot.creatorDirection).toEqual({
      presentationChange: originalDirection,
    });
    expect(originalRequest.frozenSnapshot.resolvedContext).toMatchObject({
      scene: { id: "scene_arrival" },
      characters: [expect.objectContaining({ id: "char_ruanxing" })],
      locations: [expect.objectContaining({ id: "loc_control" })],
      props: [expect.objectContaining({ id: "prop_lever" })],
      dialogueCues: [expect.objectContaining({ id: "cue_b1", speakerId: "char_ruanxing" })],
    });
    const originalTemplate = await readJson(path.join(originalPackage, "completion-manifest.example.json"));
    expect(originalTemplate).toMatchObject({ jobId: original.id, requestHash: original.requestHash, outputs: [{ role: "original" }] });

    await writeDelivery(workbench.imageExchangeRoot, original, "original-browser-001", "original");
    await page.getByTestId(`refresh-image-job-${original.id}`).click();
    await expect.poll(async () => (await latestImageJob(request, workbench.apiOrigin, projectId)).deliveries[0]?.state).toBe("accepted");
    const acceptedOriginal = await latestImageJob(request, workbench.apiOrigin, projectId);
    const originalCandidate = acceptedOriginal.deliveries[0].candidates[0].assetId;

    await page.getByTestId(`keep-candidate-${originalCandidate}`).click();
    await page.getByTestId("visual-intent-source-refs").fill("retained P0 image fixture for P1 browser regression");
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await page.getByLabel("审核兼容性说明").fill("The accepted original candidate matches the approved arrival shot.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("intent r1");
    await recordSamePersonReview(page, "char_ruanxing");
    await page.getByTestId("preview-subset-length").selectOption("1");
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("still-animatic")).toBeVisible();

    const refinementDirection = "Keep the reviewed parent framing; improve facial clarity under practical control-panel lighting.";
    await page.getByTestId(`prepare-refinement-${originalCandidate}`).click();
    await page.getByTestId("image-job-target").selectOption(`refinement:${originalCandidate}`);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue("");
    await page.getByTestId("image-job-presentation-change").fill(refinementDirection);
    await prepareImageJob(page, projectId, "prepare-image-job");
    const refinement = await latestImageJob(request, workbench.apiOrigin, projectId);
    expect(refinement.request.kind).toBe("refinement");
    await copyImageJob(page, projectId, refinement.id);
    const refinementPackage = path.join(workbench.imageExchangeRoot, "jobs", refinement.id, "package");
    const refinementRequest = await readJson(path.join(refinementPackage, "request.json"));
    expect(refinementRequest.references).toEqual(expect.arrayContaining([
      expect.objectContaining({ role: "character_identity:char_ruanxing" }),
      expect.objectContaining({ role: "parent_output" }),
    ]));
    expect(refinementRequest.frozenSnapshot.creatorDirection).toEqual({ presentationChange: refinementDirection });
    expect(refinementRequest.frozenSnapshot.reviewedVisualIntent).toMatchObject({
      assetId: originalCandidate, selectionRevision: 1, visualIntentRevision: 1,
      intent: expect.objectContaining({ role: "shot_keyframe" }),
    });
    const refinementTemplate = await readJson(path.join(refinementPackage, "completion-manifest.example.json"));
    expect(refinementTemplate).toMatchObject({ jobId: refinement.id, requestHash: refinement.requestHash, outputs: [{ role: "refinement" }] });

    await writeDelivery(workbench.imageExchangeRoot, refinement, "refinement-browser-001", "refinement");
    await page.getByTestId(`refresh-image-job-${refinement.id}`).click();
    await expect.poll(async () => (await imageJob(request, workbench.apiOrigin, projectId, refinement.id)).deliveries[0]?.state).toBe("accepted");

    // Copy another valid refinement first, then revise the role-specific
    // VisualIntent through the normal browser editor. Its Refresh must retain
    // the late receipt as inapplicable rather than publish changed-brief bytes.
    await page.getByTestId("image-job-presentation-change").fill("Retain the parent composition while balancing the practical lights.");
    await prepareImageJob(page, projectId, "prepare-image-job");
    const staleRefinement = await latestImageJob(request, workbench.apiOrigin, projectId);
    await copyImageJob(page, projectId, staleRefinement.id);
    await page.getByTestId("visual-intent-source-refs").fill("retained P0 image fixture revised after copied refinement");
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(/已保存 r2/)).toBeVisible();
    await writeDelivery(workbench.imageExchangeRoot, staleRefinement, "refinement-stale-browser-001", "refinement");
    await page.getByTestId(`refresh-image-job-${staleRefinement.id}`).click();
    await expect.poll(async () => (await imageJob(request, workbench.apiOrigin, projectId, staleRefinement.id)).deliveries[0]?.state).toBe("inapplicable");
    const staleResult = await imageJob(request, workbench.apiOrigin, projectId, staleRefinement.id);
    expect(staleResult.deliveries[0]).toMatchObject({ state: "inapplicable", candidates: [] });
    await expect(page.getByTestId(`image-job-${staleRefinement.id}`)).toContainText("INAPPLICABLE");

    // A delivery with a changed manifest must be rejected through the same
    // browser Refresh path; absence is the only non-error waiting state.
    await page.getByTestId("image-job-target").selectOption("original");
    await page.getByTestId("image-job-presentation-change").fill("Browser-check the manifest integrity before accepting this original delivery.");
    await prepareImageJob(page, projectId, "prepare-image-job");
    const tampered = await latestImageJob(request, workbench.apiOrigin, projectId);
    await copyImageJob(page, projectId, tampered.id);
    await writeDelivery(workbench.imageExchangeRoot, tampered, "tampered-browser-001", "original");
    const tamperedManifest = path.join(workbench.imageExchangeRoot, "jobs", tampered.id, "delivery", "completion.json");
    const tamperedContents = await readJson(tamperedManifest);
    tamperedContents.requestHash = "0".repeat(64);
    await writeFile(tamperedManifest, JSON.stringify(tamperedContents), "utf8");
    const rejectedRefresh = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/image-jobs/${tampered.id}/refresh`);
    await page.getByTestId(`refresh-image-job-${tampered.id}`).click();
    expect((await rejectedRefresh).status()).toBeGreaterThanOrEqual(400);
    await expect(page.getByRole("alert")).toBeVisible();
    await expect.poll(async () => (await imageJob(request, workbench.apiOrigin, projectId, tampered.id)).deliveries[0]?.state).toBe("rejected");
    await page.screenshot({ path: usabilityScreenshot });
  });
});

async function createCanonicalProject(request: import("@playwright/test").APIRequestContext, apiOrigin: string): Promise<string> {
  const storyboard = structuredClone(demoProject.storyboard);
  const firstShot = storyboard.shots.find((shot) => shot.id === "shot_01")!;
  firstShot.propIds = ["prop_lever"];
  firstShot.requiredEntityStates = [{ entityType: "prop", entityId: "prop_lever", state: "broken" }];
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `p1-image-brief-${Date.now()}` },
    data: {
      brief: demoProject.brief,
      initialStages: [
        { stage: "story_bible", payload: demoProject.storyBible },
        { stage: "story_graph", payload: demoProject.storyGraph },
        { stage: "scene_beats", payload: demoProject.sceneBeats },
        { stage: "storyboard", payload: storyboard },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json() as { id: string }).id;
}

async function prepareImageJob(page: import("@playwright/test").Page, projectId: string, testId: string): Promise<void> {
  const prepared = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/image-jobs`);
  await page.getByTestId(testId).click();
  const response = await prepared;
  expect(response.status(), await response.text()).toBe(201);
}

async function copyImageJob(page: import("@playwright/test").Page, projectId: string, jobId: string): Promise<void> {
  const copied = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/image-jobs/${jobId}/copy`);
  await page.getByTestId(`copy-image-job-${jobId}`).click();
  const response = await copied;
  expect(response.ok(), await response.text()).toBeTruthy();
}

async function recordSamePersonReview(page: import("@playwright/test").Page, characterId: string): Promise<void> {
  const panel = page.getByTestId("same-person-review-panel");
  await expect(panel).toBeVisible();
  await panel.getByLabel("身份对比说明").fill("Human reviewer confirms the stable face, build, and visible character anchors.");
  await panel.getByLabel("镜头状态说明").fill("Wardrobe, action, and lighting are reviewed as frozen shot state, not durable identity.");
  await panel.getByLabel("复核备注").fill("P1.5 browser regression review; no automated face-recognition claim.");
  await panel.getByTestId(`same-person-judgment-${characterId}`).selectOption("pass");
  await panel.getByTestId("record-same-person-review").click();
  await expect(panel.getByText("当前复核", { exact: false })).toBeVisible();
}

async function latestImageJob(request: import("@playwright/test").APIRequestContext, apiOrigin: string, projectId: string): Promise<ImageJob> {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/image-jobs`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const payload = await response.json() as { jobs: ImageJob[] };
  expect(payload.jobs.length).toBeGreaterThan(0);
  // The public history is newest-first, matching the workbench display.
  return payload.jobs[0]!;
}

async function imageJob(request: import("@playwright/test").APIRequestContext, apiOrigin: string, projectId: string, jobId: string): Promise<ImageJob> {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/image-jobs`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const payload = await response.json() as { jobs: ImageJob[] };
  const job = payload.jobs.find((item) => item.id === jobId);
  expect(job).toBeDefined();
  return job!;
}

async function writeDelivery(root: string, job: ImageJob, deliveryId: string, role: "original" | "refinement"): Promise<void> {
  const content = await readFile(retainedStill);
  const outputRoot = path.join(root, "jobs", job.id, "delivery", "outputs");
  const packageRequest = await readJson(path.join(root, "jobs", job.id, "package", "request.json"));
  const identityReferenceHashes = packageRequest.references
    .filter((reference: { role: string }) => reference.role.startsWith("character_identity:"))
    .map((reference: { sha256: string }) => reference.sha256);
  const identityAware = packageRequest.packageVersion === 3 && identityReferenceHashes.length > 0;
  await mkdir(outputRoot, { recursive: true });
  await writeFile(path.join(outputRoot, "candidate.png"), content);
  await writeFile(path.join(root, "jobs", job.id, "delivery", "completion.json"), JSON.stringify({
    schemaVersion: identityAware ? 2 : 1,
    jobId: job.id,
    requestHash: job.requestHash,
    deliveryId,
    actualPrompt: "Regression delivery built from the retained P0 image file; no new ImageGen call was made.",
    outputs: [{ filename: "candidate.png", sha256: createHash("sha256").update(content).digest("hex"), role }],
    toolEvidence: { tool: "codex_imagegen", taskId: "p1-browser-regression-retained-asset", available: true },
    ...(identityAware ? {
      referenceUse: {
        viewedReferenceHashes: identityReferenceHashes,
        identityNotes: "Fixture attestation only; creator review remains required.",
      },
      executorProvenance: {
        codeRevision: "a".repeat(40),
        skillVersion: "plotloom-image-specialist.v1",
        skillHash: "b".repeat(64),
      },
    } : {}),
    limitations: ["Retained asset regression only; no new image generation was requested."],
  }), "utf8");
}

async function readJson(pathname: string): Promise<any> {
  return JSON.parse(await readFile(pathname, "utf8"));
}
