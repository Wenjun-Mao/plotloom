import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";

test("same project recovers a stale rebuild target, requires fresh reviews and permits subsequent graph revision", async ({ page, request, workbench }, info) => {
  test.setTimeout(180_000);
  // A current-schema, deterministic source-review fixture establishes the
  // installed baseline. Rebuild and graph edits below use real public UI/API.
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot], { cwd: path.resolve(".."), encoding: "utf8" }).trim();
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const endpoint = `${root}/production-bridge`;
  const bridgePath = `/api/v2/projects/${id}/production-bridge`;
  const original = await json(request.get(endpoint));
  const first = original.installation.cuts[0];
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=storyboard&entity=shot%3A${first.shotId}`);
  await page.getByLabel("审核人标签").fill("Original rebuild fixture review");
  await page.getByRole("button", { name: "批准当前分镜", exact: true }).click();
  await expect(page.getByText("当前批准：Original rebuild fixture review", { exact: true })).toBeVisible();
  const originalReview = await json(request.get(`${root}/storyboard-review`));
  expect(originalReview.activeApproval.subjectRevision).toBe(1);

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const panel = page.getByTestId("production-bridge");
  const prepare = panel.getByRole("button", { name: "准备重建提案", exact: true });
  const prepareResponse = page.waitForResponse(response => new URL(response.url()).pathname === `${bridgePath}/proposals` && response.request().method() === "POST");
  await prepare.click();
  const prepared = await json(await prepareResponse);
  expect(prepared.installation).toEqual(original.installation);
  expect(prepared.proposal.intentPackage.reviewState).toBe("pending");
  expect(prepared.proposal.presentation.reviewed).toBe(false);
  await expect(panel.getByRole("button", { name: "确认投产提案", exact: true })).toBeDisabled();

  // A second actor changes the actual canonical replacement target during
  // review. The rejected target must have a visible route to fresh preparation.
  const stages = await json(request.get(`${root}/stages`));
  const board = stages.stages.find((stage: { head: { stage: string } }) => stage.head.stage === "storyboard");
  await json(request.patch(`${root}/stages/storyboard`, { data: {
    expectedRevision: board.head.revision,
    payload: { ...board.payload, shots: board.payload.shots.map((shot: { id: string; title: string }) => shot.id === first.shotId ? { ...shot, title: `${shot.title} · reviewed elsewhere` } : shot) },
  } }));
  await page.reload();
  await expect(panel).toContainText("上下文已过期");
  await expect(panel.getByTestId("installed-production")).toContainText("需要重建");
  await expect(prepare).toBeEnabled();
  await expect(panel.locator(".bridge-intent-field textarea").first()).toBeDisabled();
  await expect(panel.getByRole("button", { name: "保存戏剧意图整包", exact: true })).toBeDisabled();
  await expect(panel.getByRole("button", { name: "继续：打开第一个镜头", exact: true })).toHaveCount(0);
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(viewport);
    await panel.getByTestId("installed-production").scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`rebuild-stale-${viewport.width}x${viewport.height}.png`) });
  }
  const freshResponse = page.waitForResponse(response => new URL(response.url()).pathname === `${bridgePath}/proposals` && response.request().method() === "POST");
  await prepare.click();
  const fresh = await json(await freshResponse);
  expect(fresh.proposal.replacementTarget.storyboard.revision).toBe(2);
  expect(fresh.installation.admissionId).toBe(original.installation.admissionId);
  expect(fresh.installation.status).toBe("outdated");
  expect(fresh.proposal.intentPackage.reviewState).toBe("pending");
  expect(fresh.proposal.presentation.reviewed).toBe(false);

  await page.reload();
  const presentation = panel.getByTestId("production-presentation-review");
  for (const source of fresh.proposal.presentation.sources) {
    await presentation.getByLabel(`归属 ${source.id} 1`, { exact: true }).selectOption(source.kind === "dialogue" ? "dialogue" : "physical");
    if (source.kind !== "dialogue") await presentation.getByLabel(`画面描述 ${source.id} 1`, { exact: true }).fill(source.sourceText);
  }
  await presentation.getByRole("checkbox").check();
  const presentationResponse = page.waitForResponse(response => response.url().endsWith("/proposals/presentation") && response.request().method() === "PUT");
  await presentation.getByRole("button", { name: "保存呈现方式审阅", exact: true }).click();
  expect((await presentationResponse).ok()).toBe(true);
  const fields = panel.locator(".bridge-intent-field textarea");
  for (let index = 0; index < await fields.count(); index++) await fields.nth(index).fill(`重建审阅的场次与节拍目的 ${index + 1}`);
  await panel.getByRole("button", { name: "保存戏剧意图整包", exact: true }).click();
  await expect(panel.getByRole("button", { name: "确认投产提案", exact: true })).toBeEnabled();
  const acceptResponse = page.waitForResponse(response => new URL(response.url()).pathname === `${bridgePath}/accept` && response.request().method() === "POST");
  await panel.getByRole("button", { name: "确认投产提案", exact: true }).click();
  const accepted = await json(await acceptResponse);
  expect(accepted.status).toBe("accepted");
  expect(accepted.installation.status).toBe("current");
  expect(accepted.installation.admissionId).not.toBe(original.installation.admissionId);
  expect(accepted.installation.installedStageRevisions.storyboard).toBe(3);
  const rebuiltReview = await json(request.get(`${root}/storyboard-review`));
  expect(rebuiltReview.activeApproval).toBeNull();
  expect(rebuiltReview.decisions).toHaveLength(1);
  expect(rebuiltReview.decisions[0].decision.id).toBe(originalReview.activeApproval.id);

  await panel.getByRole("button", { name: "继续：打开第一个镜头", exact: true }).click();
  await expect(page.getByTestId("shot-preparation-summary")).toContainText("无当前批准（历史决定不适用）");
  await page.getByLabel("审核人标签").fill("Fresh rebuild review");
  await page.getByRole("button", { name: "批准当前分镜", exact: true }).click();
  await expect(page.getByText("当前批准：Fresh rebuild review", { exact: true })).toBeVisible();
  await page.reload();
  expect((await json(request.get(`${root}/storyboard-review`))).activeApproval.subjectRevision).toBe(3);
  expect((await json(request.get(endpoint))).installation).toEqual(accepted.installation);

  // Installed production no longer prevents confirming and applying a real
  // footage change. It instead becomes outdated until the source reviews rebuild.
  await page.getByRole("button", { name: "创作工作台", exact: true }).click();
  await page.locator('[data-creator-node="choose"] .creator-node-select').click();
  await page.getByRole("tab", { name: "故事", exact: true }).click();
  await page.getByLabel("包含画面与剧本场景").check();
  await page.getByRole("button", { name: "保存图草稿", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "确认图内容", exact: true }).click();
  await expect(page.getByRole("button", { name: "应用到故事路线", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "应用到故事路线", exact: true }).click();
  await expect(page.locator(".creator-inspector > footer")).toContainText("当前图内容已应用到故事路线");
  const revised = await json(request.get(endpoint));
  expect(revised.installation.admissionId).toBe(accepted.installation.admissionId);
  expect(revised.installation.status).toBe("outdated");
  expect(revised.preparation.status).toBe("unavailable");
  expect((await json(request.get(`${root}/runs`))).runs).toEqual([]);
  expect(errors).toEqual([]);
});
