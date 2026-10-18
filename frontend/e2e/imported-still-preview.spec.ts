import { navigateToSecondaryTool, openMediaPreparation, openMediaKeyframes } from "./workbench-controls";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";
import { reviewedFixtureSource, saveFixtureTargetIntent, reviewFixtureTarget } from "./fixtures/reviewed-frame-reuse";
import { captureRestartEvidence, createCanonicalProject, createReviewedPreviewProject, developmentStillPaths } from "./imported-still-preview-fixtures";

test.describe("P0 imported still preview journey", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("imports four candidates and independently reviews three shots before preview playback", async ({ page, request, workbench }) => {
    const projectId = await createCanonicalProject(request, workbench.apiOrigin);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await navigateToSecondaryTool(page, "分镜工作台");
    await openMediaPreparation(page);
    await openMediaKeyframes(page);

    await page.getByLabel("审核人标签").fill("P0 file-SQLite browser reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(page.getByText("当前批准：P0 file-SQLite browser reviewer", { exact: true })).toBeVisible();

    // Four independent provenance records make the comparison surface real;
    // the production contract itself has no fixed import-count limit.
    await page.getByLabel("来源声明").fill("Direct development-session images generated with imagegen on 2026-09-11");
    const candidateCards = page.getByLabel("候选图像比较").locator(".media-candidate");
    for (let index = 0; index < 4; index += 1) {
      await page.getByTestId("managed-image-upload").setInputFiles(developmentStillPaths[index]);
      await expect(candidateCards).toHaveCount(index + 1);
    }
    const cards = candidateCards;
    // Keeping each real image is an explicit comparison action; it adds the
    // candidate without treating the last imported file as a hidden default.
    await cards.nth(0).getByTestId(/^keep-candidate-/).click();
    await page.getByLabel("审核兼容性说明").fill("Unsubmitted observations for fixture A only.");
    await cards.nth(1).getByTestId(/^keep-candidate-/).click();
    await expect(page.getByLabel("审核兼容性说明")).toHaveValue("");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    await expect(page.getByText("正在比较两个候选", { exact: false })).toBeVisible();
    await cards.nth(0).getByTestId(/^keep-candidate-/).click();
    await page.getByTestId("visual-intent-source-refs").fill("development session image · fixture A");
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await page.getByLabel("审核兼容性说明").fill("The retained still matches the approved first-shot composition.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("画面意图 r1");
    const source = await reviewedFixtureSource(request, workbench.apiOrigin, projectId);
    const reference = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-references`, { data: {
      characterId: "char_ruanxing", authority: "story_bible", primaryAssetId: source.binding.assetId,
      complementaryAssetIds: [], expectedReferenceRevision: 0, reviewer: "Codex",
      notes: "Offline fixture identity reference for independent target review; not human creative acceptance.",
    } });
    expect(reference.ok(), await reference.text()).toBeTruthy();

    await page.getByRole("combobox", { name: "当前镜头", exact: true }).selectOption("shot_02");
    await cards.nth(0).getByTestId(/^keep-candidate-/).click();
    await expect(page.getByLabel("审核兼容性说明")).toHaveValue("");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    const secondIntent = await saveFixtureTargetIntent(page, request, workbench.apiOrigin, projectId, source, "shot_02");
    await page.getByLabel("审核兼容性说明").fill("The retained fixture still is explicitly reviewed for the second shot.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await reviewFixtureTarget(page, request, workbench.apiOrigin, projectId, source, secondIntent);
    await page.getByRole("combobox", { name: "当前镜头", exact: true }).selectOption("shot_p0_03");
    await cards.nth(0).getByTestId(/^keep-candidate-/).click();
    await expect(page.getByLabel("审核兼容性说明")).toHaveValue("");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    const thirdIntent = await saveFixtureTargetIntent(page, request, workbench.apiOrigin, projectId, source, "shot_p0_03");
    await page.getByLabel("审核兼容性说明").fill("The retained fixture still is explicitly reviewed for the third shot.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await reviewFixtureTarget(page, request, workbench.apiOrigin, projectId, source, thirdIntent);
    await expect(page.getByText("所有镜头已有当前审核关键帧", { exact: false })).toBeVisible();
    await page.getByRole("combobox", { name: "当前镜头", exact: true }).selectOption("shot_01");
    await page.getByTestId("preview-subset-length").selectOption("3");
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    await page.getByTestId("animatic-play-pause").click();
    await page.getByTestId("animatic-seek").fill("2");
    await expect(page.getByText("shot_p0_03 · 2000 毫秒", { exact: false })).toBeVisible();

    const beforeRestart = await captureRestartEvidence(request, workbench.apiOrigin, projectId);
    expect(beforeRestart.workbench.reviewedKeyframes).toEqual(expect.arrayContaining([
      expect.objectContaining({ shotId: "shot_01", compatibilityNote: "The retained still matches the approved first-shot composition." }),
      expect.objectContaining({ shotId: "shot_02", compatibilityNote: "The retained fixture still is explicitly reviewed for the second shot." }),
      expect.objectContaining({ shotId: "shot_p0_03", compatibilityNote: "The retained fixture still is explicitly reviewed for the third shot." }),
    ]));
  });

  test("retains imported bytes and reviewed receipts across a real restart before explicit replacement", async ({ page, request, workbench }, testInfo) => {
    const { projectId } = await createReviewedPreviewProject(request, workbench.apiOrigin);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await navigateToSecondaryTool(page, "分镜工作台");
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    const cards = page.getByLabel("候选图像比较").locator(".media-candidate");
    const beforeRestart = await captureRestartEvidence(request, workbench.apiOrigin, projectId);
    // This terminates the owned FastAPI process and starts a new one with the
    // same SQLite database and ArtifactStore directory; it is intentionally
    // not a tab, navigation, or in-process state check.
    await workbench.restartBackend();
    await page.reload();
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    await page.getByRole("button", { name: "编辑镜头细节", exact: true }).click();
    await expect(page.getByTestId("still-animatic")).toBeVisible();
    const afterRestart = await captureRestartEvidence(request, workbench.apiOrigin, projectId);
    expect(afterRestart.preview).toEqual(beforeRestart.preview);
    expect(afterRestart.workbench.assets).toEqual(beforeRestart.workbench.assets);
    expect(afterRestart.workbench.visualIntents).toEqual(beforeRestart.workbench.visualIntents);
    expect(afterRestart.workbench.reviewedKeyframes).toEqual(beforeRestart.workbench.reviewedKeyframes);
    expect(afterRestart.workbench.characterReferences).toEqual(beforeRestart.workbench.characterReferences);
    expect(afterRestart.workbench.samePersonReviews).toEqual(beforeRestart.workbench.samePersonReviews);
    expect(afterRestart.originalBytes).toEqual(beforeRestart.originalBytes);
    const firstFrame = beforeRestart.preview.manifest.frames[0];
    const renderedStill = page.getByAltText(`Shot ${firstFrame.shotId} reviewed still`);
    await expect.poll(() => renderedStill.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);

    // A replacement is explicit, makes the former receipt stale, and permits
    // a new current receipt after the creator freezes the replacement.
    await page.getByRole("combobox", { name: "当前镜头", exact: true }).selectOption("shot_01");
    await openMediaPreparation(page);
    await cards.nth(1).getByTestId(/^keep-candidate-/).click();
    await expect(page.getByLabel("审核兼容性说明")).toHaveValue("");
    await page.getByTestId("visual-intent-source-refs").fill("development session image · fixture B");
    await page.getByTestId("save-visual-intent").click();
    await page.getByLabel("审核兼容性说明").fill("The replacement still matches the approved first-shot composition.");
    await page.getByTestId("select-reviewed-keyframe").click();
    await expect(page.getByText("已过期", { exact: true }).first()).toBeVisible();
    await page.getByTestId("create-still-preview").click();
    await expect(page.getByText("当前可用", { exact: true }).first()).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("p0-imported-still-preview-1440x900.png"), animations: "disabled" });
  });

  test("invalidates replaced reviewed media on a board edit, reapproves explicitly and deletes its owned project", async ({ page, request, workbench }) => {
    const { projectId, replacementAssetId } = await createReviewedPreviewProject(request, workbench.apiOrigin, true);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
    await navigateToSecondaryTool(page, "分镜工作台");
    await openMediaPreparation(page);
    await openMediaKeyframes(page);
    const cards = page.getByLabel("候选图像比较").locator(".media-candidate");
    await expect(page.getByText("当前可用", { exact: true }).first()).toBeVisible();
    // A real authored-board edit removes the approval; the workbench must
    // repaint and block a reviewed selection until the normal reapproval.
    await page.getByRole("button", { name: "编辑镜头细节", exact: true }).click();
    await page.getByLabel("标题").fill("门开（P0 reapproval check）");
    const savedBoardResponse = page.waitForResponse((response) =>
      response.request().method() === "PATCH" && new URL(response.url()).pathname ===
        `/api/v2/projects/${projectId}/stages/storyboard`,
    );
    await page.getByRole("button", { name: "保存分镜" }).click();
    const savedBoard = await savedBoardResponse;
    expect(savedBoard.ok(), await savedBoard.text()).toBeTruthy();
    expect(await savedBoard.json()).toMatchObject({ stage: "storyboard", revision: 2 });
    // Save completion includes canonical remount and refreshed Approval reads.
    // Open the new revision's disclosure, not the old instance still in flight.
    await expect(page.getByRole("button", { name: "保存分镜", exact: true })).toBeEnabled();
    await openMediaKeyframes(page);
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    await expect(page.getByText("请先批准当前分镜；导入、比较和意图细化仍可继续。", { exact: true })).toBeVisible();
    await page.getByLabel("审核人标签").fill("P0 reapproval reviewer");
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    await expect(page.getByText("当前批准：P0 reapproval reviewer", { exact: true })).toBeVisible();
    await expect(page.getByText("尚缺 3 个审核关键帧", { exact: false })).toBeVisible();
    await openMediaPreparation(page);
    await cards.nth(1).getByTestId(/^keep-candidate-/).click();
    await expect(page.getByText(/已保存 r1/)).toBeVisible();
    await expect(page.getByLabel("审核兼容性说明")).toHaveValue("");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeDisabled();
    await page.getByLabel("审核兼容性说明").fill("Reapproved board compatibility is explicit, not inherited.");
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeEnabled();
    const reapprovedSelectionAck = page.waitForResponse(response =>
      response.request().method() === "POST" && new URL(response.url()).pathname ===
        `/api/v2/projects/${projectId}/reviewed-keyframes`
        && response.request().postDataJSON().shotId === "shot_01",
    );
    await page.getByTestId("select-reviewed-keyframe").click();
    const reapprovedResponse = await reapprovedSelectionAck;
    const reapprovedSelection = await json(reapprovedResponse);
    await expect(page.getByTestId("select-reviewed-keyframe")).toBeEnabled();
    const media = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`));
    expect(media.selectionRevision).toBe(reapprovedSelection.selectionRevision);
    const reapprovedRequest = reapprovedResponse.request().postDataJSON();
    expect(reapprovedRequest.assetId).toBe(replacementAssetId);
    expect(media.reviewedKeyframes.find((binding: { id: string }) => binding.id === reapprovedSelection.id)).toMatchObject({
      id: reapprovedSelection.id, selectionRevision: reapprovedSelection.selectionRevision,
      assetId: reapprovedRequest.assetId, shotId: reapprovedRequest.shotId, sceneId: reapprovedRequest.sceneId,
      visualIntentId: reapprovedRequest.visualIntentId, visualIntentRevision: reapprovedRequest.visualIntentRevision,
      compatibilityNote: reapprovedRequest.compatibilityNote,
    });

    // Ordinary cleanup starts only after the exact final selection ACK and its
    // complete current read. Earlier rapid shot changes deliberately keep their
    // race coverage; interrupted-write lifecycle is exercised separately.
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
    const project = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`);
    const projectBody = await project.json() as { revision: number; lifecycleRevision: number; brief: { title: string } };
    const archived = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/archive`, {
      data: { expectedLifecycleRevision: projectBody.lifecycleRevision },
    });
    expect(archived.ok(), `${archived.status()} ${await archived.text()}`).toBeTruthy();
    const deletion = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/permanent-delete`, {
      data: { expectedLifecycleRevision: projectBody.lifecycleRevision + 1, expectedProjectRevision: projectBody.revision, confirmationTitle: projectBody.brief.title },
    });
    expect(deletion.status(), await deletion.text()).toBe(204);
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).status()).toBe(404);
  });
});
