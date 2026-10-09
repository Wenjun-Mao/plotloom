import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "./fixture";
import {
  createAcceptedCastOnlyProject, prepareProposalFromBrowser, proposal,
  sendProposalFromBrowser, writeProposalDelivery,
} from "./fixtures/cast-reference";

test("revises a character using a retained image without reviving its old proposal or selection", async ({ page, request, workbench }, testInfo) => {
  const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "retained-refinement");
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
  const gallery = page.getByTestId("character-reference-gallery");
  await gallery.getByLabel("想法").fill("Original hair design");
  const original = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
  const originalPackage = await sendProposalFromBrowser(page, projectId, original.id);
  await writeProposalDelivery(originalPackage.deliveryPath, original, "original-revision-fixture", "original");
  await getJson(request.post(`${endpoint}/character-reference-proposals/${original.id}/refresh`));
  await page.reload();
  await gallery.getByRole("button", { name: "选用当前图片" }).click();
  await expect(gallery).toContainText("已选择身份参考 r1");
  const originalBytes = await readFile(path.join(originalPackage.deliveryPath, "completion.json"));
  const delivered = await proposal(request, workbench.apiOrigin, projectId, original.id);
  const parentId = delivered.deliveries[0]!.candidates[0]!.assetId;
  const cast = page.getByTestId("cast-review");
  await cast.getByRole("button", { name: "编辑角色设定" }).click();
  await expect(gallery.getByRole("radio", { name: "基于图片修改" })).toBeDisabled();
  await cast.getByRole("textbox", { name: "外观", exact: true }).fill("Compact low bun and the same blue rain coat.");
  const save = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/save`);
  await cast.getByRole("button", { name: "保存角色修改" }).click();
  expect((await save).ok()).toBeTruthy();
  await page.reload();
  await expect(gallery).toContainText("已确认角色设定 r2");
  await expect(gallery).toContainText("尚未选择身份参考");
  const oldProposal = await proposal(request, workbench.apiOrigin, projectId, original.id);
  expect(oldProposal.current).toBe(false);
  const decisions = await getJson(request.get(`${endpoint}/character-references`));
  await gallery.getByRole("radio", { name: "基于图片修改" }).check();
  await expect(gallery).toContainText("这张图来自旧版角色设定，仅作为修改依据");
  await gallery.getByLabel("想法").fill("Preserve the person, follow the confirmed compact low bun design.");
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    await gallery.locator(".appearance-ideas").scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`retained-refinement-${size.width}x${size.height}.png`) });
  }
  const refinement = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
  expect(refinement.parentCandidateAssetId).toBe(parentId);
  const frozen = await sendProposalFromBrowser(page, projectId, refinement.id);
  const instructions = await readFile(path.join(frozen.packagePath, "COPY_ASSIGNMENT.txt"), "utf8");
  expect(instructions).toContain("frozen accepted Cast characterContext");
  expect(instructions).toContain("older design");
  const frozenRequest = JSON.parse(await readFile(path.join(frozen.packagePath, "request.json"), "utf8"));
  expect(frozenRequest.frozenSnapshot.acceptedCast.revision).toBe(2);
  expect(frozenRequest.frozenSnapshot.characterContext.appearance).toContain("Compact low bun");
  await writeProposalDelivery(frozen.deliveryPath, refinement, "refinement-revision-fixture", "refinement");
  await getJson(request.post(`${endpoint}/character-reference-proposals/${refinement.id}/refresh`));
  await page.reload();
  expect((await proposal(request, workbench.apiOrigin, projectId, refinement.id)).current).toBe(true);
  expect(await proposal(request, workbench.apiOrigin, projectId, original.id)).toEqual(oldProposal);
  expect(await getJson(request.get(`${endpoint}/character-references`))).toEqual(decisions);
  expect(await readFile(path.join(originalPackage.deliveryPath, "completion.json"))).toEqual(originalBytes);
  await expect(gallery).toContainText("尚未选择身份参考");
});

async function getJson<T>(response: Promise<import("@playwright/test").APIResponse>): Promise<T> {
  const result = await response;
  expect(result.ok(), await result.text()).toBeTruthy();
  return result.json() as Promise<T>;
}
