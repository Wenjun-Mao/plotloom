import { expect, test } from "./fixture";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

type PreparedOutline = { jobId: string; deliveryPath: string; packagePath: string };

test("installs Tide Light routes, survives restart, and retains a readable outline after source revision", async ({ page, request, workbench }, info) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("潮汐灯");
  await page.getByLabel("故事梗概").fill("气象站员林澈必须决定有限电缆为码头还是灯塔供电。");
  await page.getByLabel("每次完整播放的选择次数", { exact: true }).fill("1");
  await page.getByLabel("不同结局的数量", { exact: true }).fill("2");
  await page.getByLabel("分支汇合次数", { exact: true }).fill("0");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project creation did not bind an ID");
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();

  await page.getByLabel("标题").fill("潮汐灯");
  await page.getByLabel("故事内容").fill("气象站员林澈在风暴前发现电缆只能供给码头或灯塔；被困水手正等待她的决定。");
  await page.getByLabel("补充创作要求（可选）").fill("保留一处电缆选择，清楚呈现两条互斥结局。");
  await page.getByRole("button", { name: "确认改编内容" }).click();
  const preparedResponse = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/source-outline/candidates`);
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  const prepared = await preparedResponse;
  expect(prepared.ok()).toBeTruthy();
  await writeFixtureOutline(await prepared.json() as PreparedOutline);
  await page.getByRole("button", { name: "立即检查" }).click();
  await expect(page.getByText("待审阅")).toBeVisible();
  await expect(page.getByText("确认后，将以这份大纲继续设计分支和剧本；不会自动生成后续内容。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "确认使用此大纲", exact: true }).click();
  await expect(page.getByTestId("source-outline-accepted").getByText("已确认 r1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "阅读已确认大纲", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("其中的“导出 JSON”下载受隔离阅读限制，不会下载文件");
  await expect(page.getByRole("dialog").locator("iframe")).toHaveAttribute("sandbox", "allow-scripts");
  await page.getByRole("button", { name: "关闭阅读", exact: true }).click();

  const map = page.getByTestId("section-map");
  await map.getByRole("button", { name: "自行填写当前结构草稿" }).click();
  const sections = map.locator(".section-map-sections fieldset");
  for (const [index, title] of ["共同开场", "供电选择", "结局 A", "结局 B"].entries()) {
    await sections.nth(index).getByLabel("章节标题").fill(title);
    await sections.nth(index).getByLabel("章节摘要").fill("林澈在风暴前确认行动与后果。");
  }
  await sections.nth(0).getByLabel("章节摘要").fill("林澈在气象站确认电缆只够维持一个地点。 ");
  await sections.nth(1).getByLabel("章节摘要").fill("码头有电，水手靠岸；灯塔熄灭。 ");
  await sections.nth(2).getByLabel("章节摘要").fill("灯塔有电，水手跟随灯光自救；码头停摆。 ");
  await map.getByLabel("播放时显示的问题").fill("把有限电力送往哪里？");
  const outcomes = map.locator(".section-map-outcome");
  await outcomes.nth(0).getByLabel("选项文字").fill("供电码头");
  await outcomes.nth(0).getByLabel("选择后的剧情").fill("码头恢复照明，灯塔变暗。 ");
  await outcomes.nth(1).getByLabel("选项文字").fill("供电灯塔");
  await outcomes.nth(1).getByLabel("选择后的剧情").fill("灯塔照亮航道，码头停电。 ");
  await page.getByRole("button", { name: "确认并保存故事分支" }).click();
  await expect(map.getByText("当前 r1")).toBeVisible();
  await expect(map.getByRole("button", { name: "保存修改" })).toBeDisabled();
  await expect(outcomes.nth(0).getByLabel("选项文字")).toHaveValue("供电码头");
  await expect(outcomes.nth(1).getByLabel("选项文字")).toHaveValue("供电灯塔");
  await outcomes.nth(0).getByLabel("选项文字").fill("临时修改");
  await expect(map.getByRole("button", { name: "应用到故事路线" })).toBeDisabled();
  await outcomes.nth(0).getByLabel("选项文字").fill("供电码头");
  await expect(map.getByRole("button", { name: "应用到故事路线" })).toBeEnabled();
  await page.getByRole("button", { name: "应用到故事路线" }).click();
  const routeCards = map.getByTestId("section-map-route-cards");
  await expect(routeCards).toContainText("供电码头 → 结局 A");
  await expect(routeCards).toContainText("供电灯塔 → 结局 B");
  await expect(map.getByText("故事路线 r1 · 当前")).toBeVisible();
  await expect(map.getByTestId("section-map-ready")).toContainText("故事路线已就绪");
  const writes: string[] = [];
  const recordWrite = (request: { method(): string; url(): string }) => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) writes.push(request.url()); };
  page.on("request", recordWrite);
  await map.getByRole("button", { name: "继续：角色设定" }).click();
  await expect(page).toHaveURL(/[?&]stage=characters/);
  page.off("request", recordWrite);
  expect(writes).toEqual([]);

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
  await expect(page.getByTestId("section-map")).toContainText("当前 r1");
  await page.reload();
  await expect(page.getByTestId("section-map")).toContainText("当前 r1");
  await expect(page.getByTestId("section-map-route-cards")).toContainText("供电码头 → 结局 A");
  await expect(page.getByTestId("section-map").locator(".section-map-outcome").nth(0).getByLabel("选择后的剧情")).toHaveValue("码头恢复照明，灯塔变暗。 ");
  await workbench.restartBackend();
  await page.reload();
  await expect(page.getByTestId("section-map").locator(".section-map-outcome").nth(1).getByLabel("选择后的剧情")).toHaveValue("灯塔照亮航道，码头停电。 ");
  await expect(page.getByTestId("section-map-route-cards")).toContainText("供电灯塔 → 结局 B");

  const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  const current = await (await request.get(`${base}/source-outline`)).json();
  const retained = page.getByTestId("source-outline-accepted");
  const guide = page.locator(".source-workflow-source .stage-guide");
  const capture = async (name: string, target: typeof retained) => {
    for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
      await page.setViewportSize({ width, height });
      await target.evaluate(el => { el.scrollIntoView({ block: "start" }); window.scrollBy(0, -80); });
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.screenshot({ path: info.outputPath(`${name}-${width}x${height}.png`) });
    }
  };
  await retained.getByRole("button", { name: "开始新一轮大纲修订", exact: true }).click();
  const returnButton = retained.getByRole("button", { name: "返回保留的已确认大纲", exact: true });
  await expect(returnButton).toBeEnabled();
  await expect(guide).toContainText("返回保留的有效大纲");
  await capture("reopened-current-guide", guide);
  await capture("reopened-current-outline", retained);
  await returnButton.click();
  await expect(retained).toContainText("当前状态：已确认");
  await page.getByLabel("故事内容").fill("气象站员林澈改变了供电安排：先疏散码头，再照亮新的航道。");
  await page.getByRole("button", { name: "确认改编内容", exact: true }).click();
  await expect(page.getByText("改编内容 r2", { exact: true })).toBeVisible();
  await expect(returnButton).toBeDisabled();
  await expect(retained).toContainText("来源已变化，旧大纲只能阅读");
  await expect(map.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
  const revised = await (await request.get(`${base}/source-outline`)).json();
  expect(revised.acceptedOutline).toEqual(current.acceptedOutline);
  expect(revised.acceptedSectionMap).toEqual(current.acceptedSectionMap);
  expect(revised.graphAdmission.status).toBe("stale");
  await capture("stale-source-guide", guide);
  await capture("stale-retained-outline", retained);
  await capture("stale-section-map", map);
  await expect(map.locator(".section-map-actions")).toContainText("请先在上方确认当前大纲，再继续。");
  await capture("stale-section-map-actions", map.locator(".section-map-actions"));
  await expect(map.getByText("已保存的故事分支需要按当前来源、大纲与创作设置重新审阅。请先确认当前大纲，再检查并保存分支；旧内容仍保留。", { exact: true })).toBeVisible();
  const reason = map.getByText("accepted source revision changed to r2", { exact: true });
  await expect(reason).toBeHidden();
  await map.getByText("技术详情：分支过期原因", { exact: true }).click();
  await expect(reason).toBeVisible();
  await capture("stale-section-map-diagnostics", map);
  await retained.getByRole("button", { name: "阅读已确认大纲", exact: true }).click();
  await expect(page.getByRole("dialog").locator("iframe")).toHaveAttribute("sandbox", "allow-scripts");
  await expect(page.getByRole("dialog")).toContainText("阅读保留的已确认版本");
  await capture("stale-retained-report", page.getByRole("dialog"));
  await page.getByRole("button", { name: "关闭阅读", exact: true }).click();
  expect((await (await request.get(`${base}/source-outline`)).json()).acceptedOutline).toEqual(current.acceptedOutline);
  await expect(guide).toContainText("来源已变化");
  await expect(guide).not.toContainText("返回保留的有效大纲");
  await page.getByRole("button", { name: "准备大纲任务", exact: true }).click();
  await expect(guide).toContainText("大纲任务尚未交付");
  await expect(guide).not.toContainText("请准备并单独发送");
  await expect(page.getByTestId("source-outline-candidate")).toContainText("冻结来源 r2");
  await capture("revised-task-guide", guide);
  await page.getByRole("button", { name: "取消此任务", exact: true }).click();
  await expect(page.getByRole("button", { name: "重新准备大纲任务", exact: true })).toBeEnabled();
});

async function writeFixtureOutline(prepared: PreparedOutline): Promise<void> {
  const request = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8")) as {
    requestHash: string; executionPin: { specialistSkillHash: string; upstreamRevision: string; upstreamSkillHash: string };
  };
  const outline = Buffer.from(JSON.stringify({
    sections: ["S01 气象站", "S02 码头与灯塔"],
    choice: "B02 电缆供电：码头或灯塔", endings: ["码头得电", "灯塔得电"],
  }));
  const report = Buffer.from("<!doctype html><title>F1B fixture</title><p>Unreviewed fixture candidate.</p>");
  await mkdir(prepared.deliveryPath, { recursive: true });
  await writeFile(path.join(prepared.deliveryPath, "outline.json"), outline);
  await writeFile(path.join(prepared.deliveryPath, "report.html"), report);
  await writeFile(path.join(prepared.deliveryPath, "completion.json"), JSON.stringify({
    schemaVersion: 1, jobId: prepared.jobId, requestHash: request.requestHash, deliveryId: "f1b-production-browser-fixture", stage: "outline",
    candidate: { filename: "outline.json", sha256: hash(outline) }, report: { filename: "report.html", sha256: hash(report) },
    executorProvenance: {
      codeRevision: "abcdef0", skillVersion: "fixture", skillHash: request.executionPin.specialistSkillHash,
      upstreamRevision: request.executionPin.upstreamRevision, upstreamSkillHash: request.executionPin.upstreamSkillHash,
      model: "fixture", reasoningEffort: "high",
    }, limitations: ["F1B browser fixture; no creative approval."],
  }));
}

function hash(value: Buffer): string { return createHash("sha256").update(value).digest("hex"); }
