import { expect, test } from "./fixture";
import { createCanonicalProject, retainedComplementary, retainedStill } from "./image-jobs/fixture";
import { navigateToSecondaryTool, openMediaPreparation } from "./workbench-controls";
import {
  createAcceptedCastOnlyProject,
  prepareProposalFromBrowser,
  refreshProposalFromBrowser,
  sendProposalFromBrowser,
  writeProposalDelivery,
} from "./fixtures/cast-reference";

test("keeps expanded frozen image directions inside the desktop gallery", async ({ page, request, workbench }, testInfo) => {
  test.setTimeout(75_000);
  const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "long-frozen-direction");
  const direction = `保留完整冻结方向，不截断：${"UnbrokenDirectionToken".repeat(80)}\n第二行仍可阅读。`;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
  const gallery = page.getByTestId("character-reference-gallery");
  await gallery.getByLabel("想法").fill(direction);
  const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
  const paths = await sendProposalFromBrowser(page, projectId, prepared.id);
  await writeProposalDelivery(paths.deliveryPath, prepared, "long-frozen-direction-fixture", "original");
  await refreshProposalFromBrowser(page, projectId, prepared.id);
  const viewer = gallery.getByTestId("appearance-viewer");
  const details = viewer.locator("details");
  await expect(details.locator("pre")).toHaveText(direction);

  for (const { width, height } of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize({ width, height });
    await expect(details).not.toHaveAttribute("open", "");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await details.locator("summary").click();
    await expect(details).toContainText("character_reference_proposal");
    await expect(details).toContainText("unknown");
    const geometry = await viewer.evaluate(element => {
      const viewerBox = element.getBoundingClientRect();
      const imageBox = element.querySelector(".appearance-image-trigger")!.getBoundingClientRect();
      const detailsBox = element.querySelector("details")!.getBoundingClientRect();
      const prose = element.querySelector("pre")!;
      return {
        width: viewerBox.width,
        imageWidth: imageBox.width,
        detailsWidth: detailsBox.width,
        documentWidth: document.documentElement.scrollWidth,
        proseWidth: prose.clientWidth,
        proseScrollWidth: prose.scrollWidth,
      };
    });
    expect(geometry.imageWidth).toBeLessThanOrEqual(geometry.width);
    expect(geometry.detailsWidth).toBeLessThanOrEqual(geometry.width);
    expect(geometry.documentWidth).toBeLessThanOrEqual(width);
    expect(geometry.proseScrollWidth).toBeLessThanOrEqual(geometry.proseWidth + 1);
    await details.screenshot({ path: testInfo.outputPath(`frozen-direction-${width}x${height}.png`) });
    await details.locator("summary").click();
  }
  await expect(gallery).toContainText("尚未选择身份参考");
});

test("shows complete selected identity sources rather than cropped gallery thumbnails", async ({ page, request, workbench }, testInfo) => {
  // Imported retained evidence is an offline layout fixture, not native generation.
  const projectId = await createCanonicalProject(request, workbench.apiOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard`);
  await navigateToSecondaryTool(page, "分镜工作台");
  await openMediaPreparation(page);
  await page.getByLabel("来源声明").fill("Retained identity comparison layout fixture; no quality acceptance");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedStill);
  const primary = page.getByTestId("reference-primary-asset");
  await expect(primary.locator("option")).toHaveCount(2);
  const primaryId = await primary.locator("option").nth(1).getAttribute("value");
  await page.getByTestId("managed-image-upload").setInputFiles(retainedComplementary);
  await expect(primary.locator("option")).toHaveCount(3);
  const complementaryId = await primary.locator("option").evaluateAll((options, selectedId) =>
    options.map(option => (option as HTMLOptionElement).value).find(value => value && value !== selectedId), primaryId);
  expect(primaryId).toBeTruthy();
  expect(complementaryId).toBeTruthy();
  await primary.selectOption(primaryId!);
  await page.getByTestId("reference-complementary-assets").selectOption([complementaryId!]);
  await page.getByTestId("reference-reviewer").fill("Offline layout reviewer");
  await page.getByTestId("reference-notes").fill("Full reference sources must remain visible, not cropped.");
  const saved = page.waitForResponse(response => response.request().method() === "POST" &&
    new URL(response.url()).pathname === `/api/v2/projects/${projectId}/character-references`);
  await page.getByTestId("select-character-reference").click();
  expect((await saved).status()).toBe(201);
  const reference = page.getByTestId("character-reference-char_ruanxing");
  await expect(reference).toContainText("r1");
  await expect(reference.locator(".frozen-reference-set img")).toHaveCount(2);
  await expect.poll(() => reference.locator(".frozen-reference-set img").evaluateAll(images =>
    images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))).toBe(true);

  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await reference.scrollIntoViewIfNeeded();
    const frames = await reference.locator(".frozen-reference-set img").evaluateAll(images => images.map(image => {
      const element = image as HTMLImageElement;
      const style = getComputedStyle(element);
      return { fit: style.objectFit, height: element.getBoundingClientRect().height, decoded: element.complete && element.naturalWidth > 0 };
    }));
    expect(frames).toEqual([{ fit: "contain", height: 200, decoded: true }, { fit: "contain", height: 200, decoded: true }]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    await reference.screenshot({ path: testInfo.outputPath(`complete-reference-${size.width}x${size.height}.png`) });
  }
});
