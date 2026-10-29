import { test, expect } from "./vite-only-fixture";
import { languagePass, languageRequired } from "../tests/content-language-fixture";
import type { ContentLanguageStatus } from "../src/features/content-language/contracts";

test("structural delivery, UNKNOWN, semantic rejection and exact edited-candidate pass remain distinct", async ({ page, frontendOrigin }, testInfo) => {
  let status: ContentLanguageStatus = { ...languagePass(), state: "outcome_unknown", verdict: null };
  const candidates: unknown[] = [], allowances: number[] = [], observed: string[] = [];
  const retry = { retryCount: 0, automaticRetryLimit: 2, currentJobId: "local-current", currentAttemptId: "attempt-current", predecessorJobIds: [], state: "running" as const, possiblePriorCost: true };
  status.retry = retry;
  await page.route("**/api/v2/**", async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/check")) { const body = route.request().postDataJSON(); candidates.push(body.candidate); allowances.push(body.automaticRetryLimit); }
    else observed.push(url.pathname);
    await route.fulfill({ json: route.request().method() === "GET" ? languageRequired() : status });
  });
  await page.goto(`${frontendOrigin}/v2/e2e/content-language-fixture.html`);
  await expect(page.getByText("创作候选已完成结构交付，尚未经创作者采用。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "采用当前完整候选", exact: true })).toBeDisabled();
  expect(candidates).toHaveLength(0);
  await page.getByLabel("自动重试次数").fill("2");
  await page.getByRole("button", { name: "检查当前完整候选语言", exact: true }).click();
  await page.getByRole("button", { name: "核对原语言检查", exact: true }).click();
  expect(candidates).toHaveLength(1); expect(observed).toContain("/api/v2/projects/project/content-language-checks/check-original/reconcile");
  status = { ...languagePass(), retry: { ...retry, state: "ready" }, verdict: "reject", findings: [{ code: "wrong_language", span: { path: "$.entries[0].prose", start: 0, end: 2, text: "错误" }, explanation: "普通创作说明应使用英语。" }],
    issues: [{ code: "content_language_mismatch", fieldPaths: ["$.entries[0].prose"], repairFacts: { contentLocale: "en-US" } }] };
  await page.getByRole("button", { name: "核对原语言检查", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "普通创作说明应使用英语。" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("language-rejection-desktop.png"), fullPage: true });
  const editor = page.getByLabel("完整候选 JSON", { exact: true }), original = JSON.parse(await editor.inputValue());
  const edited = { ...original, entries: [{ ...original.entries[0], prose: "The keeper leaves." }] };
  await editor.fill(JSON.stringify(edited));
  await expect(page.getByRole("button", { name: "采用当前完整候选", exact: true })).toBeDisabled();
  await expect(page.getByLabel("自动重试次数")).toHaveValue("1");
  await page.getByLabel("自动重试次数").fill("0");
  status = { ...languagePass(), retry: { ...retry, automaticRetryLimit: 0, state: "ready" }, checkJobId: "edited-check", candidateHash: "c".repeat(64) };
  await page.getByRole("button", { name: "检查当前完整候选语言", exact: true }).click();
  await expect(page.getByRole("button", { name: "采用当前完整候选", exact: true })).toBeEnabled();
  expect(candidates).toEqual([original, edited]); expect(allowances).toEqual([2, 0]); expect(JSON.parse(await editor.inputValue()).entries[0].literalText).toBe("再见");
});

test("manual retry retains its command intent after a lost response and reads the current physical successor", async ({ page, frontendOrigin }, testInfo) => {
  const retry = { retryCount: 1, automaticRetriesUsed: 1, automaticRetryLimit: 1, currentJobId: "physical-failed", currentAttemptId: "attempt-failed", predecessorJobIds: ["physical-original"], state: "exhausted" as const, possiblePriorCost: true };
  const failed: ContentLanguageStatus = { ...languagePass(), state: "failed", verdict: null, retry };
  const commands: Record<string, unknown>[] = []; let observations = 0;
  await page.route("**/api/v2/**", async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/retry")) { commands.push(route.request().postDataJSON()); await route.abort("failed"); return; }
    if (url.pathname.endsWith("/reconcile")) {
      observations++;
      await route.fulfill({ json: { ...failed, state: "running", retry: { ...retry, retryCount: 2, currentJobId: "physical-next", currentAttemptId: "attempt-next", predecessorJobIds: ["physical-original", "physical-failed"], state: "running" } } }); return;
    }
    await route.fulfill({ json: failed });
  });
  await page.goto(`${frontendOrigin}/v2/e2e/content-language-fixture.html`);
  await expect(page.getByRole("button", { name: "手动重试此任务", exact: true })).toBeEnabled(); expect(commands).toHaveLength(0);
  await page.getByRole("button", { name: "手动重试此任务", exact: true }).click();
  await expect(page.getByRole("button", { name: "手动重试此任务", exact: true })).toBeDisabled();
  expect(commands).toEqual([{ commandId: expect.stringMatching(/^[a-f0-9-]{36}$/), failedJobId: "physical-failed", failedAttemptId: "attempt-failed" }]);
  await page.screenshot({ path: testInfo.outputPath("manual-retry-lost-ack.png"), fullPage: true });
  await page.getByRole("button", { name: "读取当前任务后再决定", exact: true }).click();
  await expect(page.getByRole("button", { name: "手动重试此任务", exact: true })).toHaveCount(0);
  await expect(page.getByText("另有 1 次手动重试，均保留先前任务。", { exact: true })).toBeVisible();
  expect(commands).toHaveLength(1); expect(observations).toBe(1);
  await expect(page.getByRole("button", { name: "采用当前完整候选", exact: true })).toBeDisabled();
});
