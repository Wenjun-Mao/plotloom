import { expect, projectFolderTest as test } from "./fixture";

test.describe("project-folder authoring drafts", () => {
  test("autosaves project.sqlite3 drafts, preserves stale-tab conflict, explicitly saves canon, and recovers after restart", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    const projectId = new URL(page.url()).searchParams.get("project")!;

    // The second idle timer fires while the first PUT is deliberately held.
    // Its newer typing must be queued after the first acknowledgement rather
    // than surviving only in tab session storage.
    let releaseFirstDraftRequest: (() => void) | undefined;
    const firstDraftRequestReleased = new Promise<void>((resolve) => { releaseFirstDraftRequest = resolve; });
    let markFirstDraftRequest: (() => void) | undefined;
    const firstDraftRequestStarted = new Promise<void>((resolve) => { markFirstDraftRequest = resolve; });
    let heldFirstDraftRequest = false;
    const draftEndpoint = "**/api/v2/projects/*/authoring-drafts";
    await page.route(draftEndpoint, async (route) => {
      if (!heldFirstDraftRequest && route.request().method() === "PUT") {
        heldFirstDraftRequest = true;
        markFirstDraftRequest?.();
        await firstDraftRequestReleased;
      }
      await route.continue();
    });
    await page.getByLabel("片名").fill("E2E：传输中的较早草稿");
    await firstDraftRequestStarted;
    const coalescedTitle = "E2E：传输中继续输入的最终草稿";
    await page.getByLabel("片名").fill(coalescedTitle);
    await page.waitForTimeout(800);
    releaseFirstDraftRequest?.();
    await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();
    await expect.poll(async () => (await workbenchRequest(
      workbench.apiOrigin, `/api/v2/projects/${projectId}/authoring-drafts`,
    ))[0]?.payload.title).toBe(coalescedTitle);
    await page.unroute(draftEndpoint);
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(coalescedTitle);

    const secondTab = await page.context().newPage();
    await secondTab.goto(page.url());
    await expect(secondTab.getByLabel("片名")).toHaveValue(coalescedTitle);

    const durableTitle = "E2E：只保存到项目目录的草稿";
    await page.getByLabel("片名").fill(durableTitle);
    await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();
    const canonicalBeforeSave = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}`);
    expect(canonicalBeforeSave.brief.title).toBe(coalescedTitle);
    const durableDrafts = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}/authoring-drafts`);
    expect(durableDrafts).toHaveLength(1);
    expect(durableDrafts[0]).toMatchObject({
      editorScope: "brief", entityId: "root", baseCanonicalRevision: 2,
      payload: { title: durableTitle },
    });

    // A second tab starts from the same canonical revision. Its old draft CAS
    // cannot replace the first tab's server-acknowledged authoring buffer.
    const losingTitle = "E2E：保留在冲突标签页的内容";
    await secondTab.getByLabel("片名").fill(losingTitle);
    await expect(secondTab.getByText("草稿版本已过期", { exact: true })).toBeVisible();
    await expect(secondTab.getByLabel("片名")).toHaveValue(losingTitle);
    const afterConflict = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}/authoring-drafts`);
    expect(afterConflict).toHaveLength(1);
    expect(afterConflict[0].payload.title).toBe(durableTitle);

    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(durableTitle);
    const canonicalAfterSave = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}`);
    expect(canonicalAfterSave.brief.title).toBe(durableTitle);
    expect(await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}/authoring-drafts`)).toEqual([]);

    const restartDraft = "E2E：重启后的服务器草稿";
    await page.getByLabel("片名").fill(restartDraft);
    await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();
    await workbench.restartBackend();
    await page.reload();
    await expect(page.getByText("发现未保存草稿", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "恢复草稿" }).click();
    await expect(page.getByLabel("片名")).toHaveValue(restartDraft);
    const editedAfterRecovery = "E2E：恢复后继续编辑的草稿";
    await page.getByLabel("片名").fill(editedAfterRecovery);
    await expect(page.getByText("草稿：已保存", { exact: true })).toBeVisible();
    const recoveredDrafts = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}/authoring-drafts`);
    expect(recoveredDrafts).toHaveLength(1);
    expect(recoveredDrafts[0].payload.title).toBe(editedAfterRecovery);
    const canonicalAfterRestart = await workbenchRequest(workbench.apiOrigin, `/api/v2/projects/${projectId}`);
    expect(canonicalAfterRestart.brief.title).toBe(durableTitle);
    await secondTab.close();
  });
});

async function workbenchRequest(apiOrigin: string, path: string): Promise<any> {
  const response = await fetch(`${apiOrigin}${path}`);
  expect(response.ok).toBeTruthy();
  return response.json();
}
