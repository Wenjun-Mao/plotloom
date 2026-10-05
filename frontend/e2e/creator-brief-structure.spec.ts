import { expect, test } from "./fixture";
import { json, writeDelivery, type Preparation } from "./f5a-fixture";
import path from "node:path";
import type { SourceTopology } from "../src/types";

test("returns to the current Brief and rejects a branch proposal frozen before structural edits", async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("潮汐灯");
  await page.getByLabel("故事梗概").fill("林澈先选择救援方向，再分配电力。三种结局保留不同后果。");
  await page.getByLabel("剧情节点数量上限", { exact: true }).fill("9");
  await page.getByLabel("每次完整播放的选择次数", { exact: true }).fill("2");
  await page.getByLabel("不同结局的数量", { exact: true }).fill("3");
  await page.getByLabel("每次选择的最多选项数", { exact: true }).fill("3");
  await page.getByLabel("分支汇合次数", { exact: true }).fill("1");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.getByRole("button", { name: "确认改编内容" }).click();
  const prepared = await json<Preparation>(request.post(`${base}/source-outline/candidates`));
  await writeDelivery(prepared, "outline", { source: "潮汐灯", episodes: [{ ep: 1, synopsis: "两次选择、三个结局与一个汇合点。" }] });
  await json(request.post(`${base}/source-outline/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${base}/source-outline/accept`, { data: { jobId: prepared.jobId, expectedSourceRevision: 1, expectedOutlineRevision: 0 } }));
  await page.reload();
  const map = page.getByTestId("section-map");
  const suggestion = page.getByRole("region", { name: "助手剧情分支建议" });
  await suggestion.getByRole("button", { name: "准备剧情分支建议" }).click();
  const state = await json(request.get(`${base}/branch-suggestions`));
  const topology = state.plannedTopology as SourceTopology;
  const packagePath = path.resolve(prepared.packagePath, "../..", state.candidate.jobId, "package");
  await writeDelivery({ ...prepared, jobId: state.candidate.jobId, packagePath, deliveryPath: path.resolve(packagePath, "../delivery") }, "branches", prose(topology));
  await suggestion.getByRole("button", { name: "立即检查" }).click();
  await suggestion.getByRole("button", { name: "带入可编辑草稿" }).click();
  await expect(map.locator(".section-map-sections fieldset")).toHaveCount(topology.nodes.length);
  await expect(map.locator(".section-map-choice")).toHaveCount(2);
  await expect(map.locator(".section-map-outcome")).toHaveCount(5);
  await expect(suggestion.getByRole("button", { name: "带入可编辑草稿" })).toBeDisabled();
  await map.getByRole("button", { name: "确认并保存故事分支" }).click();
  await map.getByRole("button", { name: "应用到故事路线" }).click();
  await expect(map.getByTestId("section-map-route-cards").locator("article")).toHaveCount(6);
  const retained = await json(request.get(`${base}/source-outline`));
  await suggestion.getByRole("button", { name: "放弃此建议任务" }).click();
  await suggestion.getByRole("button", { name: "准备剧情分支建议" }).click();
  const old = await json(request.get(`${base}/branch-suggestions`));
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=brief`));
  await page.getByLabel("不同结局的数量", { exact: true }).fill("2");
  await page.getByLabel("故事梗概").fill("只调整简报，保留来源正文。");
  for (const width of [1920, 1440, 1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const help = page.getByLabel("说明：每次完整播放的选择次数", { exact: true });
    await help.focus();
    const tooltip = page.getByRole("tooltip").filter({ hasText: "不是每次选择的选项数量" });
    await expect(tooltip).toBeVisible();
    await page.keyboard.press("Escape");
    await help.click();
    await expect(tooltip).toBeVisible();
    await page.screenshot({ path: info.outputPath(`brief-${width}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=brief`));
  await page.getByRole("button", { name: "返回来源与大纲" }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue(retained.source.material.text);
  await expect(map).toContainText("需要重新检查");
  expect((await request.get(`${base}/branch-suggestions/${old.candidate.jobId}/draft`)).ok()).toBe(false);
  await suggestion.getByRole("button", { name: "放弃此建议任务" }).click();
  await suggestion.getByRole("button", { name: "准备剧情分支建议" }).click();
  const fresh = await json(request.get(`${base}/branch-suggestions`));
  expect(fresh.plannedTopology.structuralParameters.endingCount).toBe(2);
  expect(fresh.plannedTopology.topologyHash).not.toBe(topology.topologyHash);
  expect((await json(request.get(`${base}/source-outline`))).acceptedOutline).toEqual(retained.acceptedOutline);
  await workbench.restartBackend();
  await page.reload();
  await expect(page.getByRole("button", { name: "阅读已确认大纲" })).toBeVisible();
  await expect(map).toContainText("需要重新检查");
});

function prose(topology: SourceTopology) {
  return {
    nodes: topology.nodes.map((node, index) => ({ id: node.id, title: `剧情 ${index + 1}`, summary: `林澈在第 ${index + 1} 段采取明确行动。` })),
    choices: topology.nodes.filter(node => node.kind === "decision").map(node => ({ nodeId: node.id, question: "林澈下一步怎样行动？", options: topology.edges.filter(edge => edge.sourceNodeId === node.id).map((edge, index) => ({ id: edge.id, label: `救援行动 ${index + 1}`, consequence: `林澈采取第 ${index + 1} 种行动，保留相应后果。` })) })),
    joins: topology.joins.map(join => ({ id: join.id, reconciliation: "人物承认先前不同的选择，再共同面对新的局面。" })),
    clarifications: ["确定性集成夹具；没有创作验收。"],
  };
}
