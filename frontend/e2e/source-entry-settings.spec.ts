import { expect, test } from "./fixture";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Page, TestInfo } from "@playwright/test";
import { demoProject } from "../src/demo";
import { json } from "./f5a-fixture";

const sourceAuditViewports = [
  { width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 },
];
async function sourceAuditCapture(page: Page, info: TestInfo, name: string) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
  await page.screenshot({ path: info.outputPath(`${name}.png`) });
}

test("unchanged original synopsis confirms without direction and freezes existing Brief settings", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  const synopsis = "许宁在小院决定放飞纸飞机，或把它收好后离开。";
  await page.getByLabel("片名").fill("风里的纸飞机");
  await page.getByLabel("故事梗概").fill(synopsis);
  await expect(page.getByRole("region", { name: "类型", exact: true })).toContainText("尚未选择");
  await page.getByRole("button", { name: "科幻", exact: true }).click();
  await page.getByText("添加题材背景自定义", { exact: true }).click();
  await page.getByLabel("题材背景自定义", { exact: true }).fill("小院传奇");
  await page.getByLabel("题材背景自定义", { exact: true }).press("Enter");
  await page.getByRole("button", { name: "真人写实", exact: true }).click();
  await page.getByRole("button", { name: "暖色", exact: true }).click();
  await page.getByRole("button", { name: "移除暖色", exact: true }).click();
  await expect(page.getByRole("button", { name: "暖色", exact: true })).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: "暖色", exact: true }).click();
  await page.getByLabel("类型细节（可选）", { exact: false }).fill("生活短片");
  await page.getByLabel("视觉风格细节（可选）", { exact: false }).fill("真人写实，柔和自然光");
  await page.getByLabel("目标游玩时长（秒）").fill("30");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project creation did not bind an ID");
  await expect(page.getByLabel("故事内容")).toHaveValue(synopsis);
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("");
  await expect(page.getByText("已从项目简报带入故事梗概。可直接使用，也可按需补充细节。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  const saved = await (await request.get(`${base}/source-outline`)).json();
  expect(saved.source.material).toMatchObject({ text: synopsis, adaptationIntent: "" });
  expect(saved.candidate).toBeNull();
  expect(saved.acceptedOutline).toBeNull();

  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await page.reload();
  await expect(page.getByRole("button", { name: "移除小院传奇", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "移除科幻", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "移除真人写实", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "移除暖色", exact: true })).toBeVisible();
  await expect(page.getByLabel("类型细节（可选）", { exact: false })).toHaveValue("生活短片");
  await expect(page.getByLabel("视觉风格细节（可选）", { exact: false })).toHaveValue("真人写实，柔和自然光");
  await page.getByRole("button", { name: "返回来源与大纲", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue(synopsis);

  const prepare = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/source-outline/candidates`);
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  const response = await prepare;
  expect(response.ok()).toBeTruthy();
  const prepared = await response.json();
  const taskCard = page.getByTestId("source-outline-candidate");
  await expect(taskCard.locator("header")).toContainText("任务尚未交付");
  await expect(taskCard.locator("header")).not.toContainText("等待助手交付");
  await expect(taskCard.getByRole("region", { name: "助手任务" })).toContainText("任务已准备，尚未发送");
  const frozen = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const { title, synopsis: briefSynopsis, ...settings } = (await (await request.get(base)).json()).brief;
  expect(title).toBe("风里的纸飞机");
  expect(briefSynopsis).toBe(synopsis);
  expect(frozen.source.text).toBe(synopsis);
  expect(frozen.source.adaptationIntent).toBe("");
  const generationSettings = { ...settings, genre: "科幻；小院传奇；生活短片", visualStyle: "真人写实；暖色；真人写实，柔和自然光" };
  expect(frozen.inputArtifacts["outline-settings.json"]).toEqual(generationSettings);
  expect(JSON.parse(await readFile(path.join(prepared.packagePath, "inputs", "outline-settings.json"), "utf8"))).toEqual(generationSettings);
  expect(settings).toMatchObject({ targetPlaythroughSeconds: 30, genre: "生活短片", visualStyle: "真人写实，柔和自然光" });
  expect((await (await request.get(`${base}/source-outline`)).json()).acceptedOutline).toBeNull();
});

test("source type changes retain writing and require a goal only for imported material", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一个有两种告别方式的故事。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const save = page.getByRole("button", { name: "确认改编内容" });
  await expect(save).toBeEnabled();
  for (const kind of ["imported_text", "existing_work"]) {
    await page.getByLabel("来源类型").selectOption(kind);
    await expect(page.getByLabel("改编目标")).toHaveAttribute("aria-required", "true");
    await expect(save).toBeDisabled();
    await expect(page.getByText("请填写改编目标，说明如何将原作改编成互动短片。", { exact: true })).toBeVisible();
  }
  await page.getByLabel("故事内容").fill("保留这个尚未确认的故事草稿。");
  await page.getByLabel("改编目标").fill("保持原作人物，把两个结局展开为动作。");
  await expect(save).toBeEnabled();
  await page.getByLabel("来源类型").selectOption("synopsis");
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("保持原作人物，把两个结局展开为动作。");
  await expect(page.getByLabel("补充创作要求（可选）")).not.toHaveAttribute("aria-required", "true");
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("保留这个尚未确认的故事草稿。");
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("保持原作人物，把两个结局展开为动作。");
});

for (const viewport of sourceAuditViewports) {
  const size = `${viewport.width}x${viewport.height}`;
  test(`Source initial read failure ends waiting and retries without writes at ${size}`, async ({ page, request, workbench }, info) => {
    await page.setViewportSize(viewport);
    const brief = { ...demoProject.brief, title: `来源初次读取 ${size}`, synopsis: "许宁在小院决定放飞纸飞机，或带着它离开。" };
    const project = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      headers: { "Idempotency-Key": `source-read-${size}` }, data: { brief },
    }));
    const root = `${workbench.apiOrigin}/api/v2/projects/${project.id}`;
    const before = await json(request.get(`${root}/source-outline`));
    const writes: string[] = [];
    page.on("request", request => {
      if (new URL(request.url()).pathname.startsWith("/api/") && !["GET", "HEAD"].includes(request.method())) writes.push(`${request.method()} ${request.url()}`);
    });
    let release!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    const url = `**/api/v2/projects/${project.id}/source-outline`;
    await page.route(url, async route => { await held; await route.fulfill({ status: 503, json: { message: "来源读取测试：服务暂不可用" } }); });
    try {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=source#source`);
      await expect(page.getByText("正在读取故事来源和当前进度。", { exact: true })).toBeVisible();
      await expect(page.getByTestId("recommended-workflow")).toContainText("正在读取来源、大纲和当前分支版本");
      await expect(page.locator(".source-workflow-source .spinner")).toBeVisible();
      await expect(page.getByRole("button", { name: "刷新", exact: true })).toBeDisabled();
      await sourceAuditCapture(page, info, "source-initial-pending");
    } finally { release(); }
    await expect(page.getByText("无法读取当前进度，请先刷新重试；保留内容不代表版本已核实。", { exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toContainText("来源读取测试：服务暂不可用");
    await expect(page.getByRole("button", { name: "刷新", exact: true })).toBeEnabled();
    const failedSpinnerCount = await page.locator(".source-workflow-source .spinner").count();
    await sourceAuditCapture(page, info, "source-initial-failed");
    await page.unroute(url);
    await page.getByRole("button", { name: "刷新", exact: true }).click();
    await expect(page.getByLabel("故事内容", { exact: false })).toHaveValue(brief.synopsis);
    await expect(page.getByTestId("source-outline-source")).toContainText("尚未保存故事内容");
    await expect(page.getByRole("button", { name: "确认改编内容", exact: true })).toBeEnabled();
    await expect(page.getByRole("button", { name: "准备大纲任务", exact: true })).toBeDisabled();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await sourceAuditCapture(page, info, "source-empty-top");
    await page.getByTestId("source-outline-candidate").scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "准备大纲任务", exact: true })).toBeInViewport();
    await sourceAuditCapture(page, info, "source-empty-prerequisite");
    expect(await json(request.get(`${root}/source-outline`))).toEqual(before);
    expect(writes).toEqual([]);
    expect(failedSpinnerCount).toBe(0);
  });

  test(`Source dirty failed refresh preserves text and archived source stays read-only at ${size}`, async ({ page, request, workbench }, info) => {
    await page.setViewportSize(viewport);
    const brief = { ...demoProject.brief, title: `来源保留草稿 ${size}`, synopsis: "城里即将断电，主角要决定先救人还是先恢复记忆。" };
    const project = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      headers: { "Idempotency-Key": `source-dirty-${size}` }, data: { brief },
    }));
    const root = `${workbench.apiOrigin}/api/v2/projects/${project.id}`;
    const material = { kind: "synopsis", title: brief.title, text: brief.synopsis, attribution: null, rightsDeclaration: null, adaptationIntent: "", inventedAdditions: null };
    await json(request.put(`${root}/source-outline/source`, { data: { expectedSourceRevision: 0, material } }));
    const before = await json(request.get(`${root}/source-outline`));
    const canonical = await json(request.get(root));
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=source#source`);
    const story = page.getByLabel("故事内容", { exact: false });
    await expect(story).toHaveValue(material.text);
    const retained = `${material.text}\n这是我还没有确认的新剧情，读取与重试不得改写。`;
    await story.fill(retained);
    const writes: string[] = [];
    page.on("request", request => {
      if (new URL(request.url()).pathname.startsWith("/api/") && !["GET", "HEAD"].includes(request.method())) writes.push(`${request.method()} ${request.url()}`);
    });
    let release!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    const url = `**/api/v2/projects/${project.id}/source-outline`;
    await page.route(url, async route => { await held; await route.fulfill({ status: 503, json: { message: "来源刷新测试：服务暂不可用" } }); });
    try {
      await page.getByRole("button", { name: "刷新", exact: true }).click();
      await expect(page.getByText("正在读取故事来源和当前进度。", { exact: true })).toBeVisible();
      await expect(page.getByTestId("recommended-workflow")).toContainText("正在读取来源、大纲和当前分支版本");
      await expect(story).toHaveValue(retained); await expect(story).toBeDisabled();
      await expect(page.getByRole("button", { name: "确认改编内容", exact: true })).toBeDisabled();
      await expect(page.getByRole("button", { name: "准备大纲任务", exact: true })).toBeDisabled();
      await sourceAuditCapture(page, info, "source-dirty-pending");
      await story.scrollIntoViewIfNeeded(); await expect(story).toBeInViewport();
      await sourceAuditCapture(page, info, "source-dirty-pending-editor");
    } finally { release(); }
    await expect(page.getByRole("alert")).toContainText("来源刷新测试：服务暂不可用");
    await expect(page.getByTestId("recommended-workflow")).toContainText("先在本页刷新读取");
    await expect(story).toHaveValue(retained); await expect(story).toBeDisabled();
    await page.getByText("无法读取当前进度，请先刷新重试；保留内容不代表版本已核实。", { exact: true }).scrollIntoViewIfNeeded();
    await sourceAuditCapture(page, info, "source-dirty-failed");
    await story.scrollIntoViewIfNeeded(); await expect(story).toBeInViewport();
    await sourceAuditCapture(page, info, "source-dirty-failed-editor");
    await page.unroute(url);
    await page.getByRole("button", { name: "刷新", exact: true }).click();
    await expect(story).toBeEnabled(); await expect(story).toHaveValue(retained);
    await expect(page.getByRole("button", { name: "准备大纲任务", exact: true })).toBeEnabled();
    await sourceAuditCapture(page, info, "source-dirty-reverified");
    await story.scrollIntoViewIfNeeded(); await expect(story).toBeInViewport();
    await sourceAuditCapture(page, info, "source-dirty-reverified-editor");
    expect(await json(request.get(`${root}/source-outline`))).toEqual(before);
    expect(await json(request.get(root))).toEqual(canonical);
    expect(writes).toEqual([]);

    // Read-only is a separate disposable project, not a destructive shortcut around dirty Close.
    const archived = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      headers: { "Idempotency-Key": `source-archive-${size}` }, data: { brief: { ...brief, title: `只读来源 ${size}` } },
    }));
    const archivedRoot = `${workbench.apiOrigin}/api/v2/projects/${archived.id}`;
    await json(request.put(`${archivedRoot}/source-outline/source`, { data: { expectedSourceRevision: 0, material } }));
    await json(request.post(`${archivedRoot}/archive`, { data: { expectedLifecycleRevision: archived.lifecycleRevision } }));
    const archivedBefore = await json(request.get(`${archivedRoot}/source-outline`));
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${archived.id}&stage=source#source`);
    await expect(page.getByText("归档只读", { exact: true })).toBeVisible();
    await expect(story).toHaveValue(material.text); await expect(story).toBeDisabled();
    await expect(page.getByText("项目当前只读，可查看已有内容；不能修改来源或准备、发送新任务。", { exact: true })).toBeVisible();
    await expect(page.getByText("故事来源已确认。下一步准备大纲任务，再发送给文字创作助手。", { exact: true })).toHaveCount(0);
    await sourceAuditCapture(page, info, "source-archived-top");
    const confirm = page.getByRole("button", { name: "确认改编内容", exact: true });
    await confirm.scrollIntoViewIfNeeded(); await expect(confirm).toBeDisabled(); await expect(confirm).toBeInViewport();
    await expect(page.getByText("项目当前只读。", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "准备大纲任务", exact: true })).toBeDisabled();
    await sourceAuditCapture(page, info, "source-archived-prerequisite");
    expect(await json(request.get(`${archivedRoot}/source-outline`))).toEqual(archivedBefore);
    expect(writes).toEqual([]);
  });
}
