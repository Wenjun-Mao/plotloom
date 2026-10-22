import { readFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { createCastReadyProject } from "./fixtures/cast-reference";

test("discards a delivered proposal without deleting evidence and freezes an explicit replacement style", async ({ page, request, workbench }, testInfo) => {
  const { projectId, castPrepared } = await createCastReadyProject(request, workbench.apiOrigin, "render-choice");
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${projectId}/cast`;
  const evidence = path.join(castPrepared.deliveryPath, "cast.json");
  const original = await readFile(evidence);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
  const panel = page.getByTestId("cast-review");
  await panel.getByRole("button", { name: "放弃此角色提案", exact: true }).click();
  const prepare = panel.getByRole("button", { name: "准备角色设定任务", exact: true });
  await expect(prepare).toBeDisabled();
  const style = panel.getByRole("combobox", { name: "角色图像风格", exact: true });
  await expect(style).toHaveValue("");
  expect(await readFile(evidence)).toEqual(original);
  const discarded = await (await request.get(endpoint)).json();
  expect(discarded.candidate).toBeNull();
  expect(discarded.acceptedCast).toBeNull();

  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await style.scrollIntoViewIfNeeded();
    await expect(style).toBeVisible();
    const box = await style.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: testInfo.outputPath(`cast-render-choice-${width}x${height}.png`) });
  }
  await style.selectOption("live-action");
  await expect(prepare).toBeEnabled();
  const preparing = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/candidates`);
  await prepare.click();
  const response = await preparing;
  expect(response.ok()).toBeTruthy();
  expect(response.request().postDataJSON()).toEqual({ renderStyle: "live-action" });
  const next = await response.json();
  expect(next.jobId).not.toBe(castPrepared.jobId);
  expect(next.binding.renderContract.style).toBe("live-action");
  const frozen = JSON.parse(await readFile(path.join(next.packagePath, "inputs/cast-style-contract.json"), "utf8"));
  expect(frozen).toEqual(next.binding.renderContract);
  await expect(panel).toContainText("本次角色图像风格：真人写实");
  await page.reload();
  await expect(panel).toContainText("本次角色图像风格：真人写实");
  expect(await readFile(evidence)).toEqual(original);
});
