import { navigateToSecondaryTool, openMediaPreparation, openMediaKeyframes } from "./workbench-controls";
import { writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "./fixture";
import {
  createCanonicalProject, imageJob, latestImageJob, prepareImageJob,
  readJson, recordSamePersonReview, retainedComplementary, retainedStill,
  sendImageJob, writeDelivery,
} from "./image-jobs/fixture";

// Verification runs must not overwrite tracked creator evidence.
const usabilityScreenshot = path.join(tmpdir(), "plotloom-p1-image-workflow-usability-1440x900.png");

test.describe("P1 self-contained specialist image brief", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("prepares, sends, refreshes, refines, and invalidates a frozen brief after an intent revision", async ({
    page,
    request,
    workbench,
  }, testInfo) => {
    // This one journey verifies original acceptance, refinement acceptance, stale
    // inapplicability, and tampered-manifest rejection; give its distinct phases
    // a local budget without changing the suite's 45-second default.
    test.setTimeout(75_000);
    const projectId = await createCanonicalProject(
      request,
      workbench.apiOrigin,
    );
    await page.goto(
      `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`,
    );
    await navigateToSecondaryTool(page, "分镜工作台");
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    await page
      .getByLabel("审核人标签")
      .fill("P1 self-contained browser reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(
      page.getByText("当前批准：P1 self-contained browser reviewer", {
        exact: true,
      }),
    ).toBeVisible();

    // P1.5 v3 jobs are reference-conditioned for visible characters. Create
    // that creator decision through the workbench before requesting a job;
    // the retained file is fixture evidence, not a generated pilot result.
    await page
      .getByLabel("来源声明")
      .fill(
        "Retained P0 fixture used as a P1.5 identity-reference regression input",
      );
    await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
    const referenceAssetId = await page
      .getByTestId("reference-primary-asset")
      .locator("option")
      .nth(1)
      .getAttribute("value");
    expect(referenceAssetId).toBeTruthy();
    await page
      .getByTestId("managed-image-upload")
      .setInputFiles(retainedComplementary);
    const complementaryAssetId = await page
      .getByTestId("reference-complementary-assets")
      .locator("option")
      .nth(1)
      .getAttribute("value");
    expect(complementaryAssetId).toBeTruthy();
    await page
      .getByTestId("reference-primary-asset")
      .selectOption(referenceAssetId!);
    await page
      .getByTestId("reference-complementary-assets")
      .selectOption([complementaryAssetId!]);
    await page
      .getByTestId("reference-reviewer")
      .fill("P1.5 browser reference reviewer");
    await page
      .getByTestId("reference-notes")
      .fill(
        "Stable facial and build guidance only; pose, wardrobe, and lighting remain owned by each frozen shot.",
      );
    await page.getByTestId("select-character-reference").click();
    await expect(
      page.getByTestId("character-reference-char_ruanxing"),
    ).toContainText("r1");

    const originalDirection =
      "Render the approved arrival shot with clear practical control-room lighting and readable facial detail.";
    const shotPicker = page.getByLabel("当前媒体镜头");
    const originalShotId = await shotPicker.inputValue();
    const alternateShotId = await shotPicker
      .locator("option")
      .nth(1)
      .getAttribute("value");
    await page
      .getByTestId("image-job-presentation-change")
      .fill(originalDirection);
    await page.getByTestId("discard-image-job-direction").click();
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(
      "",
    );
    await expect(page.getByTestId("discard-image-job-direction")).toHaveCount(
      0,
    );
    await page
      .getByTestId("image-job-presentation-change")
      .fill(originalDirection);
    if (alternateShotId && alternateShotId !== originalShotId) {
      await shotPicker.selectOption(alternateShotId);
      await expect(
        page.getByTestId("image-job-presentation-change"),
      ).toHaveValue("");
      await shotPicker.selectOption(originalShotId);
      await expect(
        page.getByTestId("image-job-presentation-change"),
      ).toHaveValue(originalDirection);
    }
    await page.reload();
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(
      originalDirection,
    );
    await page.evaluate(() => {
      const key = "plotloom:image-job-direction-drafts:v1";
      const drafts = JSON.parse(window.sessionStorage.getItem(key) || "{}");
      const first = Object.keys(drafts)[0];
      if (first) drafts[first].contextId = "obsolete-context";
      window.sessionStorage.setItem(key, JSON.stringify(drafts));
    });
    await page.reload();
    await openMediaPreparation(page);
    await expect(page.getByTestId("image-job-direction-stale")).toBeVisible();
    await page.getByRole("button", { name: "确认后恢复到当前上下文" }).click();
    await expect(page.getByTestId("image-job-direction-stale")).toHaveCount(0);
    const otherProjectId = await createCanonicalProject(
      request,
      workbench.apiOrigin,
    );
    await page.goto(
      `${workbench.frontendOrigin}/v2/?project=${otherProjectId}&stage=storyboard`,
    );
    await openMediaPreparation(page);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(
      "",
    );
    await page
      .getByTestId("image-job-presentation-change")
      .fill("This direction must remain isolated in the other project.");
    await page.goto(
      `${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`,
    );
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(
      originalDirection,
    );
    await prepareImageJob(page, projectId, "prepare-image-job");
    const original = await latestImageJob(
      request,
      workbench.apiOrigin,
      projectId,
    );
    await expect(page.getByTestId(`image-job-${original.id}`)).toBeVisible();
    const originalPackage = await sendImageJob(page, projectId, original.id);
    await expect(page.getByTestId(`image-job-${original.id}`)).toContainText(
      "已发送给图像生成助手",
    );
    await page.getByTestId(`refresh-image-job-${original.id}`).click();
    await expect(page.getByTestId(`image-job-${original.id}`)).toContainText(
      "尚未收到交付",
    );
    expect(
      (await imageJob(request, workbench.apiOrigin, projectId, original.id)).deliveries,
    ).toEqual([]);

    const originalRequest = await readJson(
      path.join(originalPackage.packagePath, "request.json"),
    );
    expect(originalRequest).toMatchObject({
      schemaVersion: 3,
      packageVersion: 5,
      jobId: original.id,
    });
    expect(originalRequest.references).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ role: "character_identity:char_ruanxing" }),
      ]),
    );
    expect(originalRequest.frozenSnapshot.creatorDirection).toEqual({
      presentationChange: originalDirection,
    });
    expect(originalRequest.frozenSnapshot.resolvedContext).toMatchObject({
      scene: { id: "scene_arrival" },
      characters: [expect.objectContaining({ id: "char_ruanxing" })],
      locations: [expect.objectContaining({ id: "loc_control" })],
      props: [expect.objectContaining({ id: "prop_lever" })],
      dialogueCues: [
        expect.objectContaining({ id: "cue_b1", speakerId: "char_ruanxing" }),
      ],
    });
    const originalTemplate = await readJson(
      path.join(originalPackage.packagePath, "completion-manifest.example.json"),
    );
    expect(originalTemplate).toMatchObject({
      jobId: original.id,
      requestHash: original.requestHash,
      outputs: [{ role: "original" }],
    });

    await writeDelivery(
      originalPackage.packagePath,
      originalPackage.deliveryPath,
      original,
      "original-browser-001",
      "original",
    );
    await page.getByTestId(`refresh-image-job-${original.id}`).click();
    await expect
      .poll(
        async () =>
          (await latestImageJob(request, workbench.apiOrigin, projectId))
            .deliveries[0]?.state,
      )
      .toBe("accepted");
    const acceptedOriginal = await latestImageJob(
      request,
      workbench.apiOrigin,
      projectId,
    );
    const originalCandidate =
      acceptedOriginal.deliveries[0].candidates[0].assetId;

    await page.getByTestId(`keep-candidate-${originalCandidate}`).click();
    await page
      .getByTestId("visual-intent-source-refs")
      .fill("retained P0 image fixture for P1 browser regression");
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await page
      .getByLabel("审核兼容性说明")
      .fill(
        "The accepted original candidate matches the approved arrival shot.",
      );
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByTestId("current-reviewed-keyframe")).toContainText(
      "intent r1",
    );
    await recordSamePersonReview(page, "char_ruanxing");
    const frozenComparison = page.getByTestId("frozen-reference-comparison");
    await expect(
      frozenComparison.getByTestId(`frozen-reference-${referenceAssetId}`),
    ).toBeVisible();
    await expect(
      frozenComparison.getByTestId(`frozen-reference-${complementaryAssetId}`),
    ).toBeVisible();
    const frozenImages = frozenComparison.locator("img");
    await expect(frozenImages).toHaveCount(3);
    for (let index = 0; index < 3; index += 1) {
      const image = frozenImages.nth(index);
      await expect(image).toHaveCSS("object-fit", "contain");
      const box = await image.boundingBox();
      expect(box?.width).toBeGreaterThan(180);
      expect(box?.height).toBeGreaterThanOrEqual(200);
    }
    await frozenComparison.scrollIntoViewIfNeeded();
    const frozenComparisonScreenshot = testInfo.outputPath(
      "p15-frozen-reference-comparison-viewport-1440x900.png",
    );
    await page.screenshot({ path: frozenComparisonScreenshot });
    await testInfo.attach("p15 frozen reference comparison", {
      path: frozenComparisonScreenshot,
      contentType: "image/png",
    });
    await page.getByTestId("preview-subset-length").selectOption("1");
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    await page.reload();
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    await expect(page.getByTestId("still-animatic")).toBeVisible();

    const refinementDirection =
      "Keep the reviewed parent framing; improve facial clarity under practical control-panel lighting.";
    await page.getByTestId(`prepare-refinement-${originalCandidate}`).click();
    await page
      .getByTestId("image-job-target")
      .selectOption(`refinement:${originalCandidate}`);
    await expect(page.getByTestId("image-job-presentation-change")).toHaveValue(
      "",
    );
    await page
      .getByTestId("image-job-presentation-change")
      .fill(refinementDirection);
    await prepareImageJob(page, projectId, "prepare-image-job");
    const refinement = await latestImageJob(
      request,
      workbench.apiOrigin,
      projectId,
    );
    expect(refinement.request.kind).toBe("refinement");
    const refinementPackage = await sendImageJob(page, projectId, refinement.id);
    const refinementRequest = await readJson(
      path.join(refinementPackage.packagePath, "request.json"),
    );
    expect(refinementRequest.references).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ role: "character_identity:char_ruanxing" }),
        expect.objectContaining({ role: "parent_output" }),
      ]),
    );
    expect(refinementRequest.frozenSnapshot.creatorDirection).toEqual({
      presentationChange: refinementDirection,
    });
    expect(refinementRequest.frozenSnapshot.reviewedVisualIntent).toMatchObject(
      {
        assetId: originalCandidate,
        selectionRevision: 1,
        visualIntentRevision: 1,
        intent: expect.objectContaining({ role: "shot_keyframe" }),
      },
    );
    const refinementTemplate = await readJson(
      path.join(refinementPackage.packagePath, "completion-manifest.example.json"),
    );
    expect(refinementTemplate).toMatchObject({
      jobId: refinement.id,
      requestHash: refinement.requestHash,
      outputs: [{ role: "refinement" }],
    });

    await writeDelivery(
      refinementPackage.packagePath,
      refinementPackage.deliveryPath,
      refinement,
      "refinement-browser-001",
      "refinement",
    );
    await page.getByTestId(`refresh-image-job-${refinement.id}`).click();
    await expect
      .poll(
        async () =>
          (
            await imageJob(
              request,
              workbench.apiOrigin,
              projectId,
              refinement.id,
            )
          ).deliveries[0]?.state,
      )
      .toBe("accepted");

    // Send another valid refinement first, then revise the role-specific
    // VisualIntent through the normal browser editor. Its Refresh must retain
    // the late receipt as inapplicable rather than publish changed-brief bytes.
    await page
      .getByTestId("image-job-presentation-change")
      .fill(
        "Retain the parent composition while balancing the practical lights.",
      );
    await prepareImageJob(page, projectId, "prepare-image-job");
    const staleRefinement = await latestImageJob(
      request,
      workbench.apiOrigin,
      projectId,
    );
    const staleRefinementPackage = await sendImageJob(
      page, projectId, staleRefinement.id,
    );
    await page
      .getByTestId("visual-intent-source-refs")
      .fill("retained P0 image fixture revised after sent refinement");
    const revisedIntentResponse = page.waitForResponse((response) =>
      response.request().method() === "POST" && new URL(response.url()).pathname ===
        `/api/v2/projects/${projectId}/managed-assets/${originalCandidate}/visual-intents`,
    );
    await page.getByTestId("save-visual-intent").click();
    const revisedIntent = await revisedIntentResponse;
    expect(revisedIntent.status()).toBe(201);
    expect(await revisedIntent.json()).toMatchObject({
      assetId: originalCandidate, revision: 2,
      intent: { sourceRefs: ["retained P0 image fixture revised after sent refinement"] },
    });
    // A ready binding removal clears retention (ADR 0103), unlike read
    // withdrawal. Explicitly keep the original again to inspect its saved r2.
    await expect(page.getByTestId("current-reviewed-keyframe")).toHaveCount(0);
    await expect(page.getByTestId(`keep-candidate-${originalCandidate}`)).toHaveAttribute("aria-pressed", "false");
    await page.getByTestId(`keep-candidate-${originalCandidate}`).click();
    await expect(page.getByText(/已保存 r2/)).toBeVisible();
    await writeDelivery(
      staleRefinementPackage.packagePath,
      staleRefinementPackage.deliveryPath,
      staleRefinement,
      "refinement-stale-browser-001",
      "refinement",
    );
    await page.getByTestId(`refresh-image-job-${staleRefinement.id}`).click();
    await expect
      .poll(
        async () =>
          (
            await imageJob(
              request,
              workbench.apiOrigin,
              projectId,
              staleRefinement.id,
            )
          ).deliveries[0]?.state,
      )
      .toBe("inapplicable");
    const staleResult = await imageJob(
      request,
      workbench.apiOrigin,
      projectId,
      staleRefinement.id,
    );
    expect(staleResult.deliveries[0]).toMatchObject({
      state: "inapplicable",
      candidates: [],
    });
    await expect(
      page.getByTestId(`image-job-${staleRefinement.id}`),
    ).toContainText("不适用（历史）");

    // A delivery with a changed manifest must be rejected through the same
    // browser Refresh path; absence is the only non-error waiting state.
    await page.getByTestId("image-job-target").selectOption("original");
    await page
      .getByTestId("image-job-presentation-change")
      .fill(
        "Browser-check the manifest integrity before accepting this original delivery.",
      );
    await prepareImageJob(page, projectId, "prepare-image-job");
    const tampered = await latestImageJob(
      request,
      workbench.apiOrigin,
      projectId,
    );
    const tamperedPackage = await sendImageJob(page, projectId, tampered.id);
    await writeDelivery(
      tamperedPackage.packagePath,
      tamperedPackage.deliveryPath,
      tampered,
      "tampered-browser-001",
      "original",
    );
    const tamperedManifest = path.join(tamperedPackage.deliveryPath, "completion.json");
    const tamperedContents = await readJson(tamperedManifest);
    tamperedContents.requestHash = "0".repeat(64);
    await writeFile(tamperedManifest, JSON.stringify(tamperedContents), "utf8");
    const rejectedRefresh = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname ===
          `/api/v2/projects/${projectId}/image-jobs/${tampered.id}/refresh`,
    );
    await page.getByTestId(`refresh-image-job-${tampered.id}`).click();
    expect((await rejectedRefresh).status()).toBeGreaterThanOrEqual(400);
    await expect(page.getByRole("alert")).toBeVisible();
    await expect
      .poll(
        async () =>
          (await imageJob(request, workbench.apiOrigin, projectId, tampered.id))
            .deliveries[0]?.state,
      )
      .toBe("rejected");
    // Replacing the current reference does not rewrite this selected historic
    // candidate's frozen role-mapped source set.
    await page
      .getByTestId("reference-primary-asset")
      .selectOption(originalCandidate);
    await page
      .getByTestId("reference-notes")
      .fill(
        "Explicit replacement; historic jobs must retain their original frozen reference images.",
      );
    await page.getByTestId("select-character-reference").click();
    await expect(
      page.getByTestId("character-reference-char_ruanxing"),
    ).toContainText("r2");
    await expect(
      page
        .getByTestId("frozen-reference-history")
        .getByTestId(`frozen-reference-history-${referenceAssetId}`),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("frozen-reference-history")
        .getByTestId(`frozen-reference-history-${complementaryAssetId}`),
    ).toBeVisible();
    await page.screenshot({ path: usabilityScreenshot });
  });
});
