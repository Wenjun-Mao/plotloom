import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";

test("whole presentation review preserves source evidence and requires explicit complete UI review before installation", async ({ page, request, workbench }) => {
  test.setTimeout(120_000);
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot, "--pending"], { cwd: path.resolve(".."), encoding: "utf8" }).trim();
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}/production-bridge`;
  const before = await json(request.get(endpoint));
  expect(before.proposal.presentation.reviewed).toBe(false);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const panel = page.getByTestId("production-bridge");
  const presentation = panel.getByTestId("production-presentation-review");
  await expect(panel.getByRole("button", { name: "确认投产提案" })).toBeDisabled();
  await expect(presentation.getByRole("button", { name: "保存呈现归属整包" })).toBeDisabled();
  for (const source of before.proposal.presentation.sources) {
    await presentation.getByLabel(`归属 ${source.id} 1`, { exact: true }).selectOption(source.kind === "dialogue" ? "dialogue" : "physical");
    if (source.kind !== "dialogue") await presentation.getByLabel(`画面描述 ${source.id} 1`, { exact: true }).fill(source.sourceText);
  }
  await expect(presentation.getByRole("button", { name: "保存呈现归属整包" })).toBeDisabled();
  await presentation.getByRole("checkbox").check();
  const saved = page.waitForResponse(response => response.url().endsWith("/proposals/presentation") && response.request().method() === "PUT");
  await presentation.getByRole("button", { name: "保存呈现归属整包" }).click();
  expect((await saved).ok()).toBe(true);
  const after = await json(request.get(endpoint));
  expect(after.proposal.presentation.reviewed).toBe(true);
  expect(after.proposal.presentation.frozenEvidence).toEqual(before.proposal.presentation.frozenEvidence);
  expect(after.proposal.presentation.runtimeChoice).toEqual(before.proposal.presentation.runtimeChoice);
  expect(after.proposal.installable).toBe(false);
  await page.reload();
  await expect(presentation).toContainText("此来源包已保存呈现审阅");
  const textareas = panel.locator(".bridge-intent-field textarea");
  for (let index = 0; index < await textareas.count(); index++) await textareas.nth(index).fill(`明确的技术测试戏剧目的 ${index + 1}`);
  await panel.getByRole("button", { name: "保存戏剧意图整包" }).click();
  await expect(panel.getByRole("button", { name: "确认投产提案" })).toBeEnabled();
  await panel.getByRole("button", { name: "确认投产提案" }).click();
  await expect(panel).toContainText("投产提案已确认");
  const installed = await json(request.get(endpoint));
  expect(installed.runtimeChoice.prompt).toBe(before.proposal.presentation.runtimeChoice.prompt);
  expect(installed.proposal.presentation.frozenEvidence).toEqual(before.proposal.presentation.frozenEvidence);
});
