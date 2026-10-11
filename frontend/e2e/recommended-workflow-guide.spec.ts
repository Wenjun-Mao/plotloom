import { expect, test } from "./fixture";
import path from "node:path";
import { json, writeDelivery, type Preparation } from "./f5a-fixture";
import type { SourceTopology } from "../src/types";

test("names the real next branch control through delivery, import, confirmation and route application", async ({ page, request, workbench }, info) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("分支指引回归");
  await page.getByLabel("故事梗概").fill("一人决定把灯带走还是留下，两个结局互斥。");
  await page.getByLabel("每次完整播放的选择次数", { exact: true }).fill("1");
  await page.getByLabel("不同结局的数量", { exact: true }).fill("2");
  await page.getByLabel("分支汇合次数", { exact: true }).fill("0");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const outline = await json<Preparation>(request.post(`${base}/source-outline/candidates`));
  await writeDelivery(outline, "outline", { source: "指引回归", episodes: [{ ep: 1, synopsis: "一个开场与两个互斥结局。" }] });
  await json(request.post(`${base}/source-outline/candidates/${outline.jobId}/refresh`));
  await json(request.post(`${base}/source-outline/accept`, { data: { jobId: outline.jobId, expectedSourceRevision: 1, expectedOutlineRevision: 0 } }));
  let graphReadFailed = true;
  await page.route(`**/api/v2/projects/${id}/graph-workbench`, async route => {
    if (graphReadFailed && route.request().method() === "GET") {
      await route.fulfill({ status: 503, json: { detail: "Temporary graph read failure" } });
    } else await route.continue();
  });
  await page.reload();
  const guide = page.getByTestId("recommended-workflow");
  const suggestion = page.getByRole("region", { name: "助手剧情分支建议" });
  const map = page.getByTestId("section-map");
  await expect(guide).toContainText("当前 · 3/6 剧情分支");
  await expect(guide).toContainText("无法读取当前分支草稿");
  await expect(guide).toContainText("点击「刷新」");
  graphReadFailed = false;
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(guide).toContainText("点击分支区的「准备剧情分支建议」");
  const preparation = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${id}/branch-suggestions`);
  await suggestion.getByRole("button", { name: "准备剧情分支建议", exact: true }).click();
  const prepared = await json(await preparation);
  await expect(guide).toContainText("发送给文字创作助手");
  const topology = prepared.plannedTopology as SourceTopology;
  const packagePath = path.resolve(outline.packagePath, "../..", prepared.candidate.jobId, "package");
  await writeDelivery({ ...outline, jobId: prepared.candidate.jobId, packagePath, deliveryPath: path.resolve(packagePath, "../delivery") }, "branches", {
    nodes: topology.nodes.map((node, index) => ({ id: node.id, title: `灯的剧情 ${index + 1}`, summary: "角色用简单动作决定灯的去留。" })),
    choices: topology.nodes.filter(node => node.kind === "decision").map(node => ({ nodeId: node.id, question: "带走还是留下？", options: topology.edges.filter(edge => edge.sourceNodeId === node.id).map((edge, index) => ({ id: edge.id, label: index === 0 ? "带走" : "留下", consequence: "进入对应的独立结局。" })) })),
    joins: [], clarifications: ["确定性技术夹具，不作创作验收。"],
  });
  await suggestion.getByRole("button", { name: "立即检查" }).click();
  await expect(guide).toContainText("如果满意，点击「带入可编辑草稿」");
  let stageReadFailed = true;
  await page.route(`**/api/v2/projects/${id}/stages`, async route => {
    if (stageReadFailed && route.request().method() === "GET") {
      await route.fulfill({ status: 503, json: { detail: "Temporary stage read failure" } });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("HTTP 503");
  await expect(suggestion.getByRole("button", { name: "带入可编辑草稿" })).toBeDisabled();
  await expect(guide).toContainText("当前分支暂不可编辑");
  await expect(guide).not.toContainText("点击「带入可编辑草稿」");
  stageReadFailed = false;
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(guide).toContainText("如果满意，点击「带入可编辑草稿」");
  const beforeImport = await json(request.get(`${base}/source-outline`));
  expect(beforeImport.acceptedSectionMap).toBeNull();
  expect(beforeImport.graphAdmission).toBeNull();
  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await suggestion.getByRole("button", { name: "带入可编辑草稿" }).scrollIntoViewIfNeeded();
    await expect(guide).toBeVisible();
    await expect(suggestion.getByRole("button", { name: "带入可编辑草稿" })).toBeEnabled();
    await page.screenshot({ path: info.outputPath(`branch-import-next-${size.width}x${size.height}.png`) });
  }
  expect(await json(request.get(`${base}/source-outline`))).toEqual(beforeImport);
  await suggestion.getByRole("button", { name: "带入可编辑草稿" }).click();
  await expect(guide).toContainText("点击「确认并保存故事分支」");
  await expect(guide).not.toContainText("点击「带入可编辑草稿」");
  await expect(suggestion.getByRole("button", { name: "带入可编辑草稿" })).toBeDisabled();
  expect((await json(request.get(`${base}/source-outline`))).acceptedSectionMap).toBeNull();
  const title = map.locator(".section-map-sections fieldset").first().getByLabel("章节标题");
  const value = await title.inputValue();
  await title.fill("");
  await expect(guide).toContainText("先补全分支区的必填内容");
  await expect(map.getByRole("button", { name: "确认并保存故事分支", exact: true })).toBeDisabled();
  await title.fill(value);
  await map.getByRole("button", { name: "确认并保存故事分支", exact: true }).click();
  await expect(guide).toContainText("点击本页「应用到故事路线」");
  const afterSave = await json(request.get(`${base}/source-outline`));
  expect(afterSave.acceptedSectionMap.revision).toBe(1);
  expect(afterSave.graphAdmission).toBeNull();
  await title.fill(`${value} 修订`);
  await expect(guide).toContainText("点击「保存修改」");
  await expect(map.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
  await title.fill(value);
  await expect(guide).toContainText("点击本页「应用到故事路线」");
  await map.getByRole("button", { name: "应用到故事路线", exact: true }).click();
  await expect(guide.getByRole("button", { name: "进入创作工作台", exact: true })).toBeEnabled();
  await expect(guide).toContainText("当前分支已应用到故事路线");
  await title.fill(`${value} 再修订`);
  await expect(guide).toContainText("点击「保存修改」");
  await expect(guide.getByRole("button", { name: "进入创作工作台", exact: true })).toHaveCount(0);
});

test("keeps the recommended workflow visible on supported desktops and retains draft navigation protection", async ({ page, workbench }, info) => {
  await page.route("**/api/v2/runtime-capabilities", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), durableProjectDrafts: false } });
  });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("为这个只用于界面检查的故事建立项目。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const guide = page.getByTestId("recommended-workflow");
  const sourceText = page.getByLabel("故事内容");
  await expect(sourceText).toBeEnabled();
  await sourceText.fill("为这个只用于界面检查的故事补充一处尚未保存的修改。");
  await expect(guide).toContainText("故事内容有未保存修改");
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(guide).not.toContainText("故事内容有未保存修改");

  await page.getByRole("button", { name: /项目简报与创作设置/ }).click();
  await expect(guide).toBeVisible();
  await expect(guide).toContainText("当前 · 1/6 项目简报");
  await expect(guide.getByRole("button", { name: "打开来源与大纲" })).toBeVisible();

  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    const top = await guide.evaluate(element => {
      const bar = element.getBoundingClientRect();
      const toolbar = document.querySelector(".topbar")!.getBoundingClientRect();
      return { barTop: bar.top, toolbarBottom: toolbar.bottom, height: bar.height, scrollWidth: document.documentElement.scrollWidth };
    });
    expect(Math.abs(top.barTop - top.toolbarBottom)).toBeLessThanOrEqual(2);
    expect(top.scrollWidth).toBeLessThanOrEqual(size.width);
    expect(top.height).toBeLessThan(size.height - top.toolbarBottom);
    await page.screenshot({ path: info.outputPath(`recommended-workflow-${size.width}x${size.height}-collapsed.png`) });

    await guide.getByText("查看六步状态").click();
    await expect(guide.getByRole("list", { name: "推荐流程步骤" }).getByRole("listitem")).toHaveCount(6);
    await expect(guide.locator('[aria-current="step"]')).toContainText("项目简报");
    await expect(guide).toContainText("静态报告只供阅读");
    const expanded = await guide.evaluate(element => ({
      height: element.getBoundingClientRect().height,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(expanded.height).toBeLessThan(size.height);
    expect(expanded.scrollWidth).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`recommended-workflow-${size.width}x${size.height}-expanded.png`) });
    await guide.getByText("查看六步状态").click();
  }

  await page.setViewportSize({ width: 1280, height: 768 });
  await page.getByLabel("故事梗概").fill("留下一份未保存的简报草稿。 ");
  await guide.getByRole("button", { name: "打开来源与大纲" }).click();
  const draftDialog = page.getByRole("dialog", { name: "保存当前草稿？" });
  await expect(draftDialog).toBeVisible();
  await expect(draftDialog).toContainText("即将离开当前页面");
  await expect(page).toHaveURL(/stage=brief/);
});
