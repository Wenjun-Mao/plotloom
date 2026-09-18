import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, fixture, hash, json, prepare, refresh, writeDelivery } from "./f5a-fixture";

test.describe("F5A production FastAPI/file-SQLite review", () => {
  test("freezes/reloads/re-copies, validates real upstream content, accepts read-only review and persists restart", async ({ page, request, workbench }) => {
    test.setTimeout(90_000);
    const id = await createScriptProject(request, workbench.apiOrigin, "accept");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
    const panel = page.getByTestId("storyboard-review");
    const prepared = await prepare(page, panel, id);
    const frozen = await readFile(path.join(prepared.packagePath, "request.json"));
    const admission = JSON.parse(await readFile(path.join(prepared.packagePath, "inputs/storyboard-admission.json"), "utf8"));
    expect(admission.reviewTiming).toEqual({ minCutSeconds: 2, maxCutSeconds: 8, maxSegmentSeconds: 15 });
    expect(admission.sectionBindings.map((entry: any) => entry.sectionId)).toEqual(["opening", "beacon", "dock"]);
    await page.reload();
    const copied = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${prepared.jobId}/handoff`));
    await panel.getByRole("button", { name: "重新复制冻结 handoff" }).click();
    const recovered = await json(await copied);
    expect(recovered.assignment).toBe(prepared.assignment);
    expect(recovered.packagePath).toBe(prepared.packagePath);
    expect(recovered.deliveryPath).toBe(prepared.deliveryPath);
    expect(await readFile(path.join(prepared.packagePath, "request.json"))).toEqual(frozen);
    await expect(panel.getByLabel("复制给 specialist 的冻结任务")).toHaveValue(prepared.assignment);
    await writeDelivery(prepared);
    expect(hash(await readFile(path.join(prepared.deliveryPath, "storyboard.json")))).toBe("50165863d45e678c28bcf794c6f9f5444b6aa45eef2caa446595dd638313578a");
    await refresh(page, panel, id, prepared.jobId);
    await panel.getByText("查看待接受 storyboard", { exact: true }).click();
    await expect(panel.getByTestId("storyboard-cut").first()).toContainText("wide shot of a lone beacon keeper");
    await expect(panel.getByTestId("storyboard-cut").first()).toBeVisible();
    await expect(panel).toContainText("Characters: keeper");
    await expect(panel).toContainText("Props: none");
    await expect(panel).toContainText("Beats 1–1");
    const script = await fixture("script.json");
    const lines = script.episodes.flatMap((episode: any) => episode.scenes.flatMap((scene: any) => scene.flow.filter((beat: any) => beat.line).map((beat: any) => ({ ...beat, ep: episode.ep }))));
    expect(lines).toHaveLength(22);
    for (const line of lines) await expect(panel.locator(`[data-episode="${line.ep}"]`).getByTestId("storyboard-h3-direction").filter({ hasText: `<d>[Chinese] ${line.line}</d>` })).toHaveCount(1);
    await panel.getByRole("button", { name: "显式接受 review revision" }).click();
    await expect(panel).toContainText("已接受 review r1");
    await panel.getByText("查看当前已接受 storyboard", { exact: true }).click();
    await expect(panel.getByTestId("storyboard-cut").first()).toContainText("wide shot of a lone beacon keeper");
    await expect(panel.getByTestId("storyboard-cut").first()).toBeVisible();
    expect(await panel.locator("textarea:not([readonly])").count()).toBe(0);
    await panel.getByText("打开原始只读上游报告", { exact: true }).click();
    await expect(panel.frameLocator("iframe").locator("body")).toContainText("One cable. Two places need it.");
    const report = await request.get(`${endpoint(workbench.apiOrigin, id)}/candidates/${prepared.jobId}/report`);
    expect(await report.body()).toEqual(await readFile(path.join(prepared.deliveryPath, "report.html")));
    expect(report.headers()["content-security-policy"]).toContain("sandbox");
    const state = await json(request.get(endpoint(workbench.apiOrigin, id)));
    expect(state.acceptedReview.storyboard).toEqual(await fixture("storyboard.json"));
    await workbench.restartBackend(); await page.reload();
    await expect(panel).toContainText("已接受 review r1");
    await panel.getByText("查看当前已接受 storyboard", { exact: true }).click();
    for (const line of lines) await expect(panel.locator(`[data-episode="${line.ep}"]`).getByTestId("storyboard-h3-direction").filter({ hasText: `<d>[Chinese] ${line.line}</d>` })).toHaveCount(1);
    expect((await json(request.get(endpoint(workbench.apiOrigin, id)))).acceptedReview).toEqual(state.acceptedReview);
    const stages = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/stages`));
    expect(stages.stages.filter((stage: any) => stage.payload).map((stage: any) => stage.head.stage)).toEqual(["story_graph"]);
  });

  test("rejects ready review, replaces it, blocks snapshots until cancellation, and refuses late delivery", async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "cancel");
    const root = endpoint(workbench.apiOrigin, id);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
    const panel = page.getByTestId("storyboard-review");
    const first = await prepare(page, panel, id);
    await writeDelivery(first); await refresh(page, panel, id, first.jobId);
    expect((await request.post(`${root}/candidates`)).status()).toBe(409);
    await panel.getByRole("button", { name: "拒绝并取消此 review" }).click();
    await expect(panel.getByRole("button", { name: "准备并复制 storyboard specialist handoff" })).toBeEnabled();
    const next = await prepare(page, panel, id);
    expect(next.jobId).not.toBe(first.jobId);
    await expect(panel.getByRole("button", { name: "取消 handoff" })).toBeEnabled();
    const lifecycle = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    expect((await request.post(`${lifecycle}/snapshots`)).status()).toBe(409);
    expect((await request.post(`${lifecycle}/close`)).status()).toBe(409);
    await panel.getByRole("button", { name: "取消 handoff" }).click();
    await expect(panel.getByRole("button", { name: "准备并复制 storyboard specialist handoff" })).toBeEnabled();
    await writeDelivery(next);
    expect((await request.post(`${root}/candidates/${next.jobId}/refresh`)).ok()).toBeFalsy();
    const snapshot = await request.post(`${lifecycle}/snapshots`);
    expect(snapshot.ok(), await snapshot.text()).toBeTruthy();
    expect((await json(request.get(root))).candidate).toBeNull();
  });

  test("upstream edits refuse prepared re-copy and ready replay/acceptance; cancelled stale review can be replaced", async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "stale");
    const root = endpoint(workbench.apiOrigin, id);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
    const panel = page.getByTestId("storyboard-review");
    const first = await prepare(page, panel, id);
    await changeScript(request, workbench.apiOrigin, id);
    const recopy = await request.get(`${root}/candidates/${first.jobId}/handoff`);
    expect(recopy.status(), await recopy.text()).toBe(409);
    await page.reload(); await expect(panel).toContainText("上下文已过期");
    await panel.getByRole("button", { name: "取消 handoff" }).click();
    await expect(panel.getByRole("button", { name: "准备并复制 storyboard specialist handoff" })).toBeEnabled();
    const next = await prepare(page, panel, id);
    await writeDelivery(next); await refresh(page, panel, id, next.jobId);
    await changeScript(request, workbench.apiOrigin, id);
    const replay = await request.post(`${root}/candidates/${next.jobId}/refresh`);
    expect(replay.status(), await replay.text()).toBe(409);
    expect((await request.post(`${root}/accept`, { data: { jobId: next.jobId, expectedReviewRevision: next.expectedReviewRevision, binding: next.binding } })).status()).toBe(409);
    await page.reload(); await expect(panel).toContainText("上下文已过期");
    await panel.getByRole("button", { name: "拒绝并取消此 review" }).click();
    await expect(panel.getByRole("button", { name: "准备并复制 storyboard specialist handoff" })).toBeEnabled();
    const replacement = await prepare(page, panel, id);
    await writeDelivery(replacement); await refresh(page, panel, id, replacement.jobId);
    await panel.getByRole("button", { name: "显式接受 review revision" }).click();
    await expect(panel).toContainText("已接受 review r1");
    await changeScript(request, workbench.apiOrigin, id); await page.reload();
    await expect(panel).toContainText("上下文已过期");
    const current = await prepare(page, panel, id);
    expect(current.binding.scriptRevision).toBe(4);
    await expect(panel.getByRole("button", { name: "取消 handoff" })).toBeEnabled();
  });

  test("ready replay rechecks current upstream binding before idempotent return", async ({ request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "ready-replay");
    const root = endpoint(workbench.apiOrigin, id);
    const prepared = await json(request.post(`${root}/candidates`));
    await writeDelivery(prepared);
    await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
    await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
    await changeScript(request, workbench.apiOrigin, id);
    const replay = await request.post(`${root}/candidates/${prepared.jobId}/refresh`);
    expect(replay.status(), await replay.text()).toBe(409);
  });

  test("receiving gate rejects tampered params with a valid manifest and real validator rejects removed dialogue", async ({ request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "tamper");
    const root = endpoint(workbench.apiOrigin, id);
    const prepared = await json(request.post(`${root}/candidates`));
    await writeDelivery(prepared);
    const file = path.join(prepared.deliveryPath, "storyboard.json");
    const manifestFile = path.join(prepared.deliveryPath, "completion.json");
    const original = await readFile(file);
    const manifest = JSON.parse(await readFile(manifestFile, "utf8"));
    for (const changed of [
      (board: any) => { board.params.maxCutSeconds = 9; },
      (board: any) => { board.params.minCutSeconds = 1; },
      (board: any) => { board.episodes[0].segments[0].h3Prompt = board.episodes[0].segments[0].h3Prompt.replace("<d>[Chinese] One cable. Two places need it.</d>", ""); },
    ]) {
      const board = JSON.parse(original.toString()); changed(board);
      const content = Buffer.from(JSON.stringify(board)); await writeFile(file, content);
      await writeFile(manifestFile, JSON.stringify({ ...manifest, candidate: { ...manifest.candidate, sha256: hash(content) } }));
      const response = await request.post(`${root}/candidates/${prepared.jobId}/refresh`);
      expect(response.ok(), await response.text()).toBeFalsy();
      expect((await json(request.get(root))).candidate.status).toBe("prepared");
    }
    await writeFile(file, original); await writeFile(manifestFile, JSON.stringify(manifest));
    expect((await request.post(`${root}/candidates/${prepared.jobId}/refresh`)).ok()).toBeTruthy();
    const ready = (await json(request.get(root))).candidate;
    const altered = JSON.parse(original.toString()); altered.params.maxCutSeconds = 9;
    const alteredBytes = Buffer.from(JSON.stringify(altered));
    await writeFile(file, alteredBytes);
    await writeFile(manifestFile, JSON.stringify({ ...manifest, candidate: { ...manifest.candidate, sha256: hash(alteredBytes) } }));
    const replay = await request.post(`${root}/candidates/${prepared.jobId}/refresh`);
    expect(replay.status(), await replay.text()).toBe(409);
    expect((await json(request.get(root))).candidate).toEqual(ready);
  });

  test("re-copy refuses changed frozen admission bytes without rewriting the package", async ({ request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "recopy-tamper");
    const root = endpoint(workbench.apiOrigin, id);
    const prepared = await json(request.post(`${root}/candidates`));
    const admissionFile = path.join(prepared.packagePath, "inputs/storyboard-admission.json");
    const frozen = await readFile(admissionFile);
    const changed = JSON.parse(frozen.toString()); changed.reviewTiming.minCutSeconds = 1;
    const tampered = Buffer.from(JSON.stringify(changed));
    await writeFile(admissionFile, tampered);
    const recovered = await request.get(`${root}/candidates/${prepared.jobId}/handoff`);
    expect(recovered.status(), await recovered.text()).toBe(409);
    expect(await readFile(admissionFile)).toEqual(tampered);
    await writeFile(admissionFile, frozen);
    expect((await json(request.get(`${root}/candidates/${prepared.jobId}/handoff`))).assignment).toBe(prepared.assignment);
  });
});
