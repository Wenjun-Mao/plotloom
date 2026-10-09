import { expect, test } from "./fixture";

test("nested terminal review retains its dialog through settlement and refresh without real release", async ({ page, request, workbench }, testInfo) => {
  const original = await (await request.get(`${workbench.apiOrigin}/api/v2/specialists`)).json();
  const fixture = { ...original, busy: true, activeTasks: [{ jobId: "ij_synthetic" }, { jobId: "text_synthetic", projectId: "p", stage: "outline" }] };
  const writes: string[] = [];
  page.on("request", r => { if (r.url().includes("/api/") && !["GET", "HEAD"].includes(r.method())) writes.push(`${r.method()} ${new URL(r.url()).pathname}`); });
  let releaseSettlement!: () => void, releaseRefresh!: () => void;
  const heldSettlement = new Promise<void>(resolve => { releaseSettlement = resolve; });
  const heldRefresh = new Promise<void>(resolve => { releaseRefresh = resolve; });
  let settlementSucceeded = false, attempts = 0;
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await page.route("**/api/v2/specialists", async route => {
    expect(route.request().method()).toBe("GET");
    if (settlementSucceeded) await heldRefresh;
    await route.fulfill({ json: fixture });
  });
  await page.route("**/image-terminal/image_job/ij_synthetic", route => route.fulfill({ json: {
    markerHash: "a".repeat(64), marker: { jobId: "ij_synthetic", taskId: "synthetic-worker", requestHash: "b".repeat(64), reason: "浏览器测试声明：未开始生成。" },
  } }));
  await page.route("**/image-terminal/image_job/ij_synthetic/settle", async route => {
    attempts += 1;
    if (attempts === 1) {
      await heldSettlement;
      await route.fulfill({ status: 503, json: { detail: "测试终止审核失败；预约保留。" } });
    } else {
      settlementSucceeded = true;
      await route.fulfill({ json: { state: "completed" } });
    }
  });
  const dialog = page.getByRole("dialog", { name: "生成助手设置", exact: true });
  async function capture(state: string) {
    for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
      await page.setViewportSize(viewport);
      await dialog.locator(".modal-body").evaluate(el => { el.scrollTop = el.scrollHeight; });
      expect(await dialog.locator(".modal-body").evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
      expect(await dialog.locator(".modal-card").evaluate(el => {
        const bounds = el.getBoundingClientRect();
        return bounds.left >= 0 && bounds.top >= 0 && bounds.right <= innerWidth && bounds.bottom <= innerHeight;
      })).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`${state}-${viewport.width}x${viewport.height}.png`) });
    }
  }
  try {
    await page.getByRole("button", { name: "生成助手设置", exact: true }).click();
    await dialog.getByText("核对生成前阻塞的终止声明", { exact: true }).click();
    await dialog.getByLabel("终止任务所属项目 ID", { exact: true }).fill("synthetic-project");
    await dialog.getByRole("button", { name: "读取并验证终止声明", exact: true }).click();
    await dialog.getByLabel("已检查的最终回合 ID", { exact: true }).fill("synthetic-turn");
    await dialog.getByLabel("已检查的助手状态 revision", { exact: true }).fill("58");
    await dialog.getByLabel("终止审核人", { exact: true }).fill("测试审核人");
    await dialog.getByRole("checkbox").check();
    const settle = dialog.getByRole("button", { name: "记录生成前阻塞并释放此任务预约", exact: true });
    await settle.click();
    await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "关闭生成助手设置", exact: true })).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "检查此任务的结果", exact: true })).toBeDisabled();
    await expect(settle).toBeDisabled();
    await capture("settlement-pending");
    releaseSettlement();
    await expect(dialog).toContainText("测试终止审核失败；预约保留。");
    await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeEnabled();
    await expect(dialog.getByLabel("已检查的最终回合 ID", { exact: true })).toHaveValue("synthetic-turn");
    await capture("settlement-failed");
    await settle.click();
    await expect(dialog).toContainText("仅此任务预约已释放");
    await expect(dialog).toContainText("正在处理终止审核并更新任务状态…");
    await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeDisabled();
    await capture("refresh-pending");
    releaseRefresh();
    await expect(dialog.getByRole("button", { name: "关闭", exact: true })).toBeEnabled();
    await expect(dialog).not.toContainText("正在处理终止审核并更新任务状态…");
    await expect(settle).toBeDisabled();
    await capture("settlement-finished");
    expect(writes).toEqual(Array(2).fill("POST /api/v2/projects/synthetic-project/image-terminal/image_job/ij_synthetic/settle"));
    expect(await (await request.get(`${workbench.apiOrigin}/api/v2/specialists`)).json()).toEqual(original);
  } finally { releaseSettlement(); releaseRefresh(); }
});
