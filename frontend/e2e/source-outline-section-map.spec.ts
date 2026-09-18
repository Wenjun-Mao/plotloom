import { expect, test } from "./fixture";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

type PreparedOutline = { jobId: string; deliveryPath: string; packagePath: string };

test("installs the accepted Tide Light map into canonical routes, then survives reopen", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("潮汐灯");
  await page.getByLabel("故事梗概").fill("气象站员林澈必须决定有限电缆为码头还是灯塔供电。");
  await page.getByRole("button", { name: "保存简报" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project creation did not bind an ID");
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();

  await page.getByLabel("标题").fill("潮汐灯");
  await page.getByLabel("来源正文或 treatment").fill("气象站员林澈在风暴前发现电缆只能供给码头或灯塔；被困水手正等待她的决定。");
  await page.getByLabel("归属 / 署名声明").fill("F1B production-browser fixture author");
  await page.getByLabel("使用权或许可声明").fill("仅用于 Plotloom F1B 可验证测试；不构成法律确认。");
  await page.getByLabel("改编意图").fill("保留一处电缆选择，清楚呈现两条互斥结局。");
  await page.getByRole("button", { name: "保存接受的来源" }).click();
  const preparedResponse = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/source-outline/candidates`);
  await page.getByRole("button", { name: "准备 specialist handoff" }).click();
  const prepared = await preparedResponse;
  expect(prepared.ok()).toBeTruthy();
  await writeFixtureOutline(await prepared.json() as PreparedOutline);
  await page.getByRole("button", { name: "刷新 specialist delivery" }).click();
  await expect(page.getByText("可审核")).toBeVisible();
  await page.getByRole("button", { name: "显式接受此候选" }).click();
  await expect(page.getByText("已接受 r1")).toBeVisible();

  const map = page.getByTestId("section-map");
  const sections = map.locator(".section-map-sections fieldset");
  await sections.nth(0).getByLabel("章节摘要").fill("林澈在气象站确认电缆只够维持一个地点。 ");
  await sections.nth(1).getByLabel("章节摘要").fill("码头有电，水手靠岸；灯塔熄灭。 ");
  await sections.nth(2).getByLabel("章节摘要").fill("灯塔有电，水手跟随灯光自救；码头停摆。 ");
  await map.getByLabel("选择问题").fill("把有限电力送往哪里？");
  const outcomes = map.locator(".section-map-outcome");
  await outcomes.nth(0).getByLabel("选择标签").fill("供电码头");
  await outcomes.nth(0).getByLabel("后果").fill("码头恢复照明，灯塔变暗。 ");
  await outcomes.nth(1).getByLabel("选择标签").fill("供电灯塔");
  await outcomes.nth(1).getByLabel("后果").fill("灯塔照亮航道，码头停电。 ");
  await page.getByRole("button", { name: "保存明确分支映射" }).click();
  await expect(map.getByText("当前 r1")).toBeVisible();
  await expect(outcomes.nth(0).getByLabel("选择标签")).toHaveValue("供电码头");
  await expect(outcomes.nth(1).getByLabel("选择标签")).toHaveValue("供电灯塔");
  await page.getByRole("button", { name: "安装到规范路由图" }).click();
  const routeCards = map.getByTestId("section-map-route-cards");
  await expect(routeCards).toContainText("供电码头 → 结局 A");
  await expect(routeCards).toContainText("供电灯塔 → 结局 B");
  await expect(map.getByText("规范路由图 r1 · 当前")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("section-map")).toContainText("当前 r1");
  await expect(page.getByTestId("section-map-route-cards")).toContainText("供电码头 → 结局 A");
  await expect(page.getByTestId("section-map").locator(".section-map-outcome").nth(0).getByLabel("后果")).toHaveValue("码头恢复照明，灯塔变暗。 ");
  await workbench.restartBackend();
  await page.reload();
  await expect(page.getByTestId("section-map").locator(".section-map-outcome").nth(1).getByLabel("后果")).toHaveValue("灯塔照亮航道，码头停电。 ");
  await expect(page.getByTestId("section-map-route-cards")).toContainText("供电灯塔 → 结局 B");
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
