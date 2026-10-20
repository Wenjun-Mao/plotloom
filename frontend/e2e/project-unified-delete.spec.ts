import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import { access, readFile, readdir, realpath, writeFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execute = promisify(execFile);

for (const state of ["cancelled", "paused"] as const) {
  test(`controller-quiescent current ${state} project reaches strict abandonment and exact home erasure`, async ({ page, request, workbench }) => {
    test.setTimeout(120_000);
    const neighborResponse = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      data: { brief: { ...demoProject.brief, title: "严格删除保留邻居" }, initialStages: [] },
    });
    expect(neighborResponse.status()).toBe(201);
    const neighbor = await neighborResponse.json();
    const seeded = await execute("uv", ["run", "--locked", "--no-sync", "python", "frontend/e2e/fixtures/prior_abandonment_project.py",
      "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot, "--current-state", state],
      { cwd: path.resolve(".."), env: { ...process.env, PYTHONPATH: path.resolve("..") } });
    const target: { projectId: string; title: string; home: string } = JSON.parse(seeded.stdout.trim().split("\n").at(-1)!);
    const evidencePath = path.join(workbench.applicationDataRoot, "prior-abandonment-fixture.json");
    const evidence = async () => JSON.parse(await readFile(evidencePath, "utf8"));
    const original = await evidence();
    expect(original.attempts.some((attempt: { state: string }) => !["completed", "failed", "settled"].includes(attempt.state))).toBe(true);
    await workbench.restartBackend({ PLOTLOOM_E2E_PRIOR_ABANDONMENT: "1" });
    expect((await evidence()).controllerLease).toEqual({ path: path.join(await realpath(workbench.applicationDataRoot), ".autopilot-controller.lock"), held: true });
    const stops: Record<string, unknown>[] = [], erasures: Record<string, unknown>[] = [];
    page.on("request", sent => {
      if (sent.url().endsWith(`/${target.projectId}/stop-for-deletion`)) stops.push(sent.postDataJSON());
      if (sent.url().endsWith(`/${target.projectId}/abandon-and-delete`)) erasures.push(sent.postDataJSON());
    });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${neighbor.id}&stage=brief`);
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const row = page.locator(`.directory-item[data-project-id="${target.projectId}"]`);
    await row.getByRole("button", { name: "删除项目…", exact: true }).click();
    const title = state === "paused" ? "停止任务并删除项目" : "永久删除项目";
    const consent = page.getByRole("alertdialog", { name: title });
    await expect(consent).toContainText("仍未确认远程结果的任务");
    await consent.getByLabel("输入完整片名以确认删除").fill(target.title);
    await consent.getByRole("checkbox").check();
    await page.screenshot({ path: `../output/playwright/unified-delete-current-${state}.png` });
    const stopped = state === "paused" ? page.waitForResponse(response => response.url().endsWith(`/${target.projectId}/stop-for-deletion`)) : undefined;
    const deleted = page.waitForResponse(response => response.url().endsWith(`/${target.projectId}/abandon-and-delete`));
    await consent.getByRole("button", { name: `确认${title}`, exact: true }).click();
    const deletion = await deleted;
    expect(deletion.status(), await deletion.text()).toBe(204);
    let stopOutcome: { status: number; body: unknown } | null = null;
    if (stopped) {
      const stop = await stopped;
      expect(stop.status(), await stop.text()).toBe(200);
      const body = await stop.json();
      expect(body.state).toBe("cancelled");
      stopOutcome = { status: stop.status(), body };
    }
    expect(stops).toHaveLength(state === "paused" ? 1 : 0);
    expect(erasures).toHaveLength(1);
    expect(Object.keys(erasures[0]).sort()).toEqual(["acknowledgeUnknownRemote", "confirmationTitle", "expectedLifecycleRevision", "expectedProjectRevision", "previewHash", "scopeHash"].sort());
    expect(erasures[0]).toMatchObject({ confirmationTitle: target.title, acknowledgeUnknownRemote: true });
    await expect(row).toHaveCount(0);
    await expect(access(target.home)).rejects.toThrow();
    const settled = await evidence();
    expect(settled.calls.filter((call: string) => call === "revoke")).toHaveLength(1);
    expect(settled.eraseCount).toBe(1);
    expect(settled.cancelAttemptIds).toHaveLength(state === "paused" ? 1 : 0);
    expect(settled.attempts).toEqual(original.attempts);
    expect(settled.revoked).toBe(true);
    expect(settled.controllerLease.held).toBe(true);
    await workbench.restartBackend({ PLOTLOOM_E2E_PRIOR_ABANDONMENT: "1" });
    const targetRead = await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.projectId}`);
    const neighborRead = await request.get(`${workbench.apiOrigin}/api/v2/projects/${neighbor.id}`);
    expect(targetRead.status()).toBe(404);
    expect(neighborRead.status()).toBe(200);
    const evidenceOutput = path.join("..", "output", "playwright", `unified-delete-current-${state}-evidence.json`);
    await writeFile(evidenceOutput, JSON.stringify({
      fixture: "controller-quiescent recorded-current-project", initialState: state, target, neighborProjectId: neighbor.id,
      stopRequests: stops, stopOutcome, finalRequest: erasures[0], finalRequestKeys: Object.keys(erasures[0]).sort(),
      finalStatus: deletion.status(), controllerLease: settled.controllerLease,
      cancellationAttemptIds: settled.cancelAttemptIds, revocations: settled.calls.filter((call: string) => call === "revoke").length,
      erasures: settled.eraseCount, originalAttempts: original.attempts.map((attempt: { attemptId: string; state: string }) => ({ attemptId: attempt.attemptId, state: attempt.state })),
      attemptEvidenceUnchanged: true, homeAbsent: true, targetReadAfterRestart: targetRead.status(), neighborReadAfterRestart: neighborRead.status(),
    }, null, 2));
    await test.info().attach("strict-deletion-evidence", { contentType: "application/json", path: evidenceOutput });
  });
}

test("one deletion entry erases only the idle disposable home through real API and persistence", async ({ page, request, workbench }) => {
  const create = async (title: string) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
    expect(response.status()).toBe(201); return response.json();
  };
  const target = await create("统一删除空闲项目"), neighbor = await create("保留相邻项目");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${neighbor.id}&stage=brief`);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const row = page.locator(`[data-project-id="${target.id}"]`);
  await expect(row.locator(".directory-actions").getByRole("button", { name: /删除/ })).toHaveCount(1);
  await row.getByRole("button", { name: "删除项目…", exact: true }).click();
  const consent = page.getByRole("alertdialog", { name: "永久删除项目" });
  await expect(consent.getByRole("checkbox")).toHaveCount(0);
  await consent.getByLabel("输入完整片名以确认删除").fill(target.brief.title);
  await page.screenshot({ path: "../output/playwright/unified-delete-idle.png" });
  await consent.getByRole("button", { name: "确认永久删除项目", exact: true }).click();
  await expect(row).toHaveCount(0);
  expect((await readdir(workbench.outputsRoot)).some(name => name.endsWith(`__${target.id}`))).toBe(false);
  await workbench.restartBackend();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${neighbor.id}`)).status()).toBe(200);
});

for (const outcome of ["deleted", "scope_changed", "stop_lost_ack", "delete_lost_ack"] as const) {
  test(`paused automatic task has one consent and truthful ${outcome} outcome without replay`, async ({ page, request, workbench }) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: "暂停自动项目" }, initialStages: [] } });
    const target = await response.json();
    const prepared = { projectId: target.id, confirmationTitle: target.brief.title, expectedProjectRevision: 1,
      expectedLifecycleRevision: 1, scopeHash: "a".repeat(64), mode: "stop", run: { id: "exact-run", revision: 7, state: "paused" },
      blockers: [], unknownAttemptIds: ["original-unknown"], previewHash: "b".repeat(64) };
    let stops = 0, deletions = 0;
    await page.route(`**/projects/${target.id}/deletion-preview`, route => route.fulfill({ json: prepared }));
    await page.route(`**/projects/${target.id}/stop-for-deletion`, async route => {
      stops++;
      expect(route.request().postDataJSON()).toMatchObject({ expectedRunId: "exact-run", expectedRunRevision: 7, scopeHash: prepared.scopeHash });
      if (outcome === "stop_lost_ack") return route.abort("failed");
      return route.fulfill({ json: { runId: "exact-run", state: "cancelled", deletionPreview: { ...prepared, run: null,
        mode: "abandon", scopeHash: outcome === "scope_changed" ? "c".repeat(64) : prepared.scopeHash } } });
    });
    await page.route(`**/projects/${target.id}/abandon-and-delete`, async route => {
      deletions++;
      expect(route.request().postDataJSON()).toMatchObject({ scopeHash: prepared.scopeHash, acknowledgeUnknownRemote: true });
      if (outcome === "delete_lost_ack") return route.abort("failed");
      return route.fulfill({ status: 204 });
    });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const row = page.locator(`[data-project-id="${target.id}"]`);
    await row.getByRole("button", { name: "删除项目…", exact: true }).click();
    const consent = page.getByRole("alertdialog", { name: "停止任务并删除项目" });
    await expect(consent).toContainText("paused（exact-run）");
    await expect(consent).toContainText("original-unknown");
    await consent.getByLabel("输入完整片名以确认删除").fill(target.brief.title);
    await expect(consent.getByRole("button", { name: "确认停止任务并删除项目" })).toBeDisabled();
    await consent.getByRole("checkbox").check();
    await consent.getByRole("button", { name: "确认停止任务并删除项目" }).click();
    await expect(consent).toHaveCount(0);
    expect(stops).toBe(1);
    expect(deletions).toBe(["deleted", "delete_lost_ack"].includes(outcome) ? 1 : 0);
    if (outcome === "deleted") await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toBeVisible();
    else {
      await expect(row.getByRole("alert")).toContainText(outcome === "stop_lost_ack" ? "停止或删除结果未确认" : "自动运行已取消后续派发，但项目未确认删除");
      await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toHaveCount(0);
      await page.screenshot({ path: `../output/playwright/unified-delete-${outcome}.png` });
    }
  });
}
