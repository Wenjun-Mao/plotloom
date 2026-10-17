import { expect, test } from "./fixture";
import { navigateToSecondaryTool, openMediaKeyframes, openMediaPreparation } from "./workbench-controls";
import { createCanonicalProject, retainedStill, prepareImageJob, readJson, recordSamePersonReview, sendImageJob, latestImageJob, writeDelivery } from "./image-jobs/fixture";

for (const nativeSource of [false, true]) {
test(`explicit cross-shot ${nativeSource ? "native" : "imported"} pixels and scene reference retain independent target review`, async ({ page, request, workbench }) => {
  test.setTimeout(75_000);
  const projectId = await createCanonicalProject(request, workbench.apiOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await navigateToSecondaryTool(page, "分镜工作台");
  await openMediaPreparation(page);
  await openMediaKeyframes(page);
  await page.getByLabel("审核人标签").fill("Cross-shot fixture reviewer");
  await page.getByRole("button", { name: "批准当前分镜" }).click();
  await expect(page.getByText("当前批准：Cross-shot fixture reviewer", { exact: true })).toBeVisible();
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  const referenceAssetId = await page.getByTestId("reference-primary-asset").locator("option").nth(1).getAttribute("value");
  expect(referenceAssetId).toBeTruthy();
  await page.getByTestId("reference-primary-asset").selectOption(referenceAssetId!);
  await page.getByTestId("reference-reviewer").fill("Cross-shot identity reviewer");
  await page.getByTestId("reference-notes").fill("Identity appearance only, target owns action and states.");
  await page.getByTestId("select-character-reference").click();
  await expect(page.getByTestId("character-reference-char_ruanxing")).toContainText("r1");
  const picker = page.getByRole("combobox", { name: "当前镜头", exact: true });
  const sourceShotId = await picker.inputValue();
  const targetShotId = await picker.locator("option").nth(1).getAttribute("value");
  let assetId = referenceAssetId!;
  if (nativeSource) {
  // Admit a synthetic native A delivery through the real frozen package path;
  // no provider or ImageGen call occurs in this browser fixture.
  await page.getByTestId("image-job-presentation-change").fill("Source A native candidate fixture.");
  await expect(page.getByTestId("prepare-image-job")).toBeEnabled();
  await prepareImageJob(page, projectId, "prepare-image-job");
  const sourceJob = await latestImageJob(request, workbench.apiOrigin, projectId);
  const sourcePaths = await sendImageJob(page, projectId, sourceJob.id);
  await writeDelivery(sourcePaths.packagePath, sourcePaths.deliveryPath, sourceJob, "source-native-fixture", "original");
  await page.getByTestId(`refresh-image-job-${sourceJob.id}`).click();
  await expect.poll(async () => (await latestImageJob(request, workbench.apiOrigin, projectId)).deliveries[0]?.state).toBe("accepted");
  assetId = (await latestImageJob(request, workbench.apiOrigin, projectId)).deliveries[0].candidates[0].assetId;
  }
  await page.getByTestId(`keep-candidate-${assetId}`).click();
  await page.getByTestId("visual-intent-source-refs").fill("Retained scene fixture reviewed for source shot");
  await page.getByTestId("save-visual-intent").click();
  await expect(page.getByText(/已保存 r1/)).toBeVisible();
  await page.getByLabel("审核兼容性说明").fill("Source shot scene layout was inspected.");
  await page.getByTestId("select-reviewed-keyframe").click();
  await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("画面意图 r1");
  const before = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(before.ok(), await before.text()).toBeTruthy();
  const sourceBinding = (await before.json()).reviewedKeyframes.find((binding: { shotId: string }) => binding.shotId === sourceShotId);
  await picker.selectOption(targetShotId!);
  await page.getByTestId("scene-continuity-source").selectOption(sourceBinding.id);
  await page.getByTestId("image-job-presentation-change").fill("Use prior scene appearance; target controls action and framing.");
  await expect(page.getByTestId("prepare-image-job")).toBeEnabled();
  await prepareImageJob(page, projectId, "prepare-image-job");
  const job = await latestImageJob(request, workbench.apiOrigin, projectId);
  const paths = await sendImageJob(page, projectId, job.id);
  const frozen = await readJson(`${paths.packagePath}/request.json`);
  expect(frozen.references.some((item: { role: string }) => item.role === "scene_continuity")).toBe(true);
  expect(frozen.frozenSnapshot.sceneContinuity.bindingId).toBe(sourceBinding.id);
  expect(frozen.frozenSnapshot.shot.id).toBe(targetShotId);
  await writeDelivery(paths.packagePath, paths.deliveryPath, job, "cross-shot-fixture", "original");
  await page.getByTestId(`refresh-image-job-${job.id}`).click();
  await expect.poll(async () => (await latestImageJob(request, workbench.apiOrigin, projectId)).deliveries[0]?.state).toBe("accepted");
  if (nativeSource) await page.getByTestId("cross-shot-frame").selectOption(sourceBinding.id);
  else await page.getByTestId(`keep-candidate-${assetId}`).click();
  await expect(page.getByTestId("cross-shot-use-source")).toHaveValue(sourceBinding.id);
  await page.getByTestId("visual-intent-source-refs").fill("Independent target shot composition inspection");
  await page.getByTestId("save-visual-intent").click();
  await expect(page.getByText(/已保存 r2/)).toBeVisible();
  await expect(page.getByText(`目标使用：${targetShotId}`, { exact: false })).toBeVisible();
  await expect(page.getByText(`原始生成镜头：${nativeSource ? sourceShotId : "手动导入"}`, { exact: false })).toBeVisible();
  await page.getByLabel("审核兼容性说明").fill("Unchanged pixels independently inspected against target shot.");
  await page.getByTestId("select-reviewed-keyframe").click();
  await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("画面意图 r2");
  await recordSamePersonReview(page, "char_ruanxing");
  const after = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  const state = await after.json();
  expect(state.reviewedKeyframes.map((binding: { shotId: string }) => binding.shotId)).toEqual(expect.arrayContaining([sourceShotId, targetShotId]));
  const target = state.reviewedKeyframes.find((binding: { shotId: string }) => binding.shotId === targetShotId);
  expect(state.samePersonReviews.reviews.some((review: { bindingId: string; productionEligible: boolean }) => review.bindingId === target.id && review.productionEligible)).toBe(true);
  // Reselect A without changing its intent; B keeps its pinned source proof.
  await picker.selectOption(sourceShotId);
  await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("画面意图 r1");
  await page.getByLabel("审核兼容性说明").fill("A reselection with unchanged source intent.");
  const reselected = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/reviewed-keyframes"));
  await page.getByTestId("select-reviewed-keyframe").click();
  expect((await reselected).status()).toBe(201);
  await picker.selectOption(targetShotId!);
  await expect(page.getByTestId("cross-shot-use-source")).toHaveValue(sourceBinding.id);
  await expect(page.getByTestId("cross-shot-use-source").locator("option:checked")).toContainText("已冻结来源");
  for (const revision of [3, 4]) {
    await page.getByTestId("visual-intent-source-refs").fill(`B independent edit ${revision}, retaining exact prior A source`);
    await expect(page.getByTestId("save-visual-intent")).toBeEnabled();
    await page.getByTestId("save-visual-intent").click();
    await expect(page.getByText(`已保存 r${revision}；审核选择会固定这一版本。`, { exact: true })).toBeVisible();
  }
  await page.getByLabel("审核兼容性说明").fill("B reviewed again after both unselected intent edits.");
  await page.getByTestId("select-reviewed-keyframe").click();
  await expect(page.getByTestId("current-reviewed-keyframe")).toContainText("画面意图 r4");
});
}
