import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";
import { demoProject } from "../src/demo";

test("accepted bridge opens exact canonical shots and reports owner readiness without browsing writes", async ({ page, request, workbench }) => {
  test.setTimeout(120_000);
  // The shared F5A browser fixture is review-valid but deliberately not bridge-
  // installable (fractional cuts and insufficient scene duration). Seed only
  // this worker's disposable roots with the existing validated bridge fixture.
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot], {
    cwd: path.resolve(".."), encoding: "utf8",
  }).trim();
  const bridgeRoot = `${workbench.apiOrigin}/api/v2/projects/${id}/production-bridge`;
  const accepted = await json(request.get(bridgeRoot));
  expect(accepted.status).toBe("accepted");
  const otherProject = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, { headers: { "Idempotency-Key": `bridge-handoff-other-${id}` }, data: { brief: demoProject.brief } }));
  const first = accepted.proposal.cuts[0] as { shotId: string; seconds: number };
  const ending = [...accepted.proposal.cuts].reverse().find((cut: { sectionId: string }) => cut.sectionId === "ending-b") as { shotId: string; seconds: number };
  const writes: string[] = [];
  page.on("request", (pendingRequest) => {
    if (pendingRequest.url().includes("/api/v2/") && pendingRequest.method() !== "GET") writes.push(`${pendingRequest.method()} ${pendingRequest.url()}`);
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const bridge = page.getByTestId("production-bridge");
  await expect(bridge).toContainText("投产提案已确认");
  const workflow = page.getByRole("navigation", { name: "创作流程" });
  await workflow.getByRole("link", { name: "来源与大纲" }).click();
  await page.getByLabel("来源正文或 treatment").fill("Unsaved local source draft — do not discard on shot handoff");
  await workflow.getByRole("link", { name: "分镜评审" }).click();
  await bridge.getByText("查看场次与镜头").click();
  await bridge.getByRole("button", { name: `在分镜工作台打开 ${first.shotId}` }).click();
  await expect(page).toHaveURL(new RegExp("stage=source#storyboard-review$"));
  await expect(bridge).toContainText("来源文字仍有未保存的编辑");
  await page.reload(); // Discard only this test-owned unsaved browser draft.
  await bridge.getByText("查看场次与镜头").click();
  await bridge.getByRole("button", { name: `在分镜工作台打开 ${first.shotId}` }).click();
  await expect(page).toHaveURL(new RegExp(`stage=storyboard&entity=shot%3A${first.shotId}`));
  const summary = page.getByTestId("shot-preparation-summary");
  await expect(summary).toContainText(`当前镜头准备状态 · ${first.shotId}`);
  await expect(summary).toContainText(`精确来源时长 ${first.seconds} 秒`);
  await expect(summary).toContainText("缺少当前批准");
  await expect(summary).toContainText("视频后端：已配置");
  await expect(summary.getByTestId("shot-duration-compatibility")).toContainText("不在当前请求目录");

  await page.reload();
  await expect(summary).toContainText(`当前镜头准备状态 · ${first.shotId}`);
  await page.goBack();
  await expect(bridge).toContainText("投产提案已确认");
  await page.goForward();
  await expect(summary).toContainText(`当前镜头准备状态 · ${first.shotId}`);
  await summary.getByRole("button", { name: "返回分镜评审" }).click();
  await expect(page).toHaveURL(new RegExp("stage=source#storyboard-review$"));
  await bridge.getByText("查看场次与镜头").click();
  await bridge.getByRole("button", { name: `在分镜工作台打开 ${ending.shotId}` }).click();
  await expect(summary).toContainText(`当前镜头准备状态 · ${ending.shotId}`);
  await expect(summary).toContainText(`精确来源时长 ${ending.seconds} 秒`);

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${otherProject.id}&stage=storyboard&entity=shot%3A${ending.shotId}`);
  await expect(page.getByTestId("unknown-storyboard-entity")).toContainText("未打开其他镜头");
  await expect(page.getByTestId("shot-preparation-summary")).toHaveCount(0);

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=storyboard&entity=shot%3Ano-longer-owned`);
  await expect(page.getByTestId("unknown-storyboard-entity")).toContainText("未打开其他镜头");
  await expect(page.getByTestId("shot-preparation-summary")).toHaveCount(0);
  expect(writes).toEqual([]);

  // Mutate only this disposable fixture after browsing proof: downstream
  // Storyboard revision drift leaves source acceptance intact, but removes
  // its installed-cut handoff.
  const stages = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/stages`));
  const board = stages.stages.find((stage: { head: { stage: string } }) => stage.head.stage === "storyboard");
  expect(board).toBeTruthy();
  await json(request.patch(`${workbench.apiOrigin}/api/v2/projects/${id}/stages/storyboard`, { data: {
    expectedRevision: board.head.revision,
    payload: { ...board.payload, shots: board.payload.shots.map((shot: { id: string; title: string }) => shot.id === first.shotId ? { ...shot, title: `${shot.title} · revised` } : shot) },
  } }));
  const drifted = await json(request.get(bridgeRoot));
  expect(drifted.status).toBe("accepted");
  expect(drifted.installedStoryboardCurrent).toBe(false);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  await expect(bridge).toContainText("投产提案已确认");
  await bridge.getByText("查看场次与镜头").click();
  await expect(bridge.getByRole("button", { name: `在分镜工作台打开 ${first.shotId}` })).toHaveCount(0);

  // Source drift is separately represented by the bridge's stale status.
  const project = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`));
  const patched = await json(request.patch(`${workbench.apiOrigin}/api/v2/projects/${id}`, { data: {
    expectedRevision: project.revision, brief: { ...project.brief, shotCountPolicy: "strict" },
  } }));
  expect(patched.brief.shotCountPolicy).toBe("strict");
  expect((await json(request.get(bridgeRoot))).status).toBe("stale");
  await page.reload();
  expect(await page.evaluate(async (projectId) => (await (await fetch(`/api/v2/projects/${projectId}/production-bridge`)).json()).status, id)).toBe("stale");
  await expect(bridge).toContainText("上下文已过期");
  await bridge.getByText("查看场次与镜头").click();
  await expect(bridge.getByRole("button", { name: `在分镜工作台打开 ${first.shotId}` })).toHaveCount(0);
});
