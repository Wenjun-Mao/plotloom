import { expect, test } from "./fixture";
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
