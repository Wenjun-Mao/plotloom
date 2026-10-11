import { expect, test } from "./fixture";
import { json, writeDelivery, type Preparation } from "./f5a-fixture";
import path from "node:path";
import type { SourceTopology } from "../src/types";

test("structural help reserves normal-flow space without intercepting required fields", async ({ page, workbench }, info) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  const labels = ["每次完整播放的选择次数", "不同结局的数量", "剧情节点数量上限", "每次选择的最多选项数", "分支汇合次数"];
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    const shotRangeGrid = page.getByRole("spinbutton", { name: "最少", exact: true }).locator("xpath=../..");
    expect(await shotRangeGrid.evaluate(element => getComputedStyle(element).gridTemplateColumns.split(" ").length)).toBe(2);
    for (const [index, label] of labels.entries()) {
      const help = page.getByRole("button", { name: `说明：${label}`, exact: true });
      // Normal document scrolling must respect all sticky workspace chrome.
      await help.evaluate(element => {
        const group = element.closest(".field-grid")!;
        const top = Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom));
        window.scrollTo(0, group.getBoundingClientRect().top + window.scrollY - top - 12);
      });
      await help.hover();
      const tooltip = page.getByRole("tooltip");
      await expect(tooltip.locator("strong")).toHaveText(label);
      const toolbarBottom = await page.evaluate(() => Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom)));
      const initialBounds = (await tooltip.boundingBox())!;
      const overshoot = initialBounds.y + initialBounds.height - size.height;
      if (overshoot > 0) {
        const trigger = (await help.boundingBox())!;
        // Browser scrolling is integral; round the measured fractional overflow up.
        const adjustment = Math.ceil(overshoot);
        // Prove this trigger and explanation can coexist; focus/pinning cannot waive hover.
        expect(trigger.y - adjustment).toBeGreaterThanOrEqual(toolbarBottom);
        await page.mouse.move(0, 0); await expect(tooltip).toHaveCount(0);
        await page.evaluate(amount => window.scrollBy(0, amount), adjustment);
        await help.hover();
        await expect(tooltip.locator("strong")).toHaveText(label);
      }
      expect(await help.evaluate(element => {
        const bounds = element.getBoundingClientRect();
        const painted = document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
        return element.contains(painted);
      })).toBe(true);
      const checkHelpViewport = async () => {
        const bounds = await tooltip.boundingBox();
        const trigger = (await help.boundingBox())!;
        expect(trigger.y).toBeGreaterThanOrEqual(toolbarBottom);
        expect(trigger.y + trigger.height).toBeLessThanOrEqual(size.height);
        expect(bounds).not.toBeNull();
        expect(bounds!.x).toBeGreaterThanOrEqual(0); expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(size.width);
        expect(bounds!.y).toBeGreaterThanOrEqual(toolbarBottom); expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(size.height);
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
      };
      await checkHelpViewport();
      await page.screenshot({ path: info.outputPath(`help-hover-${index}-${size.width}x${size.height}.png`) });
      await page.mouse.move(0, 0);
      await expect(tooltip).toHaveCount(0);
      await help.focus();
      await expect(help).toBeFocused();
      await expect(tooltip.locator("strong")).toHaveText(label);
      await tooltip.scrollIntoViewIfNeeded();
      await checkHelpViewport();
      await page.screenshot({ path: info.outputPath(`help-focus-${index}-${size.width}x${size.height}.png`) });
      await help.click();
      await expect(help).toHaveAttribute("aria-describedby", await tooltip.getAttribute("id") as string);
      const geometry = await page.locator(".context-help-dock").evaluate(dock => {
        const bounds = dock.getBoundingClientRect();
        return [...document.querySelectorAll(".structural-setting")].map(field => {
          const rect = field.getBoundingClientRect();
          return rect.bottom <= bounds.top;
        });
      });
      expect(geometry.every(Boolean)).toBe(true);
      const input = page.getByRole("spinbutton", { name: label, exact: true });
      const next = page.getByRole("spinbutton", { name: labels[(index + 1) % labels.length], exact: true });
      const value = await input.inputValue();
      const nextValue = await next.inputValue();
      const alternative = (current: string, name: string) => name === "每次选择的最多选项数" && current === "6" ? "5" : String(Number(current) + 1);
      const changed = alternative(value, label);
      const nextChanged = alternative(nextValue, labels[(index + 1) % labels.length]);
      await input.click();
      await input.fill(changed);
      await next.click();
      await next.fill(nextChanged);
      await expect(input).toHaveValue(changed);
      await expect(next).toHaveValue(nextChanged);
      await input.fill(value);
      await next.fill(nextValue);
      await expect(input).toHaveValue(value);
      await expect(next).toHaveValue(nextValue);
      await expect(tooltip).toBeVisible();
      await help.focus();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("tooltip")).toHaveCount(0);
      await page.mouse.move(0, 0);
      await page.screenshot({ path: info.outputPath(`help-escape-${index}-${size.width}x${size.height}.png`) });
    }
    await page.getByRole("button", { name: `说明：${labels[0]}`, exact: true }).click();
    await page.screenshot({ path: info.outputPath(`help-flow-${size.width}-${size.height}.png`), fullPage: true });
    await page.getByRole("button", { name: "保存并继续到来源" }).scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "保存并继续到来源" })).toBeVisible();
    await page.getByRole("button", { name: `说明：${labels[0]}`, exact: true }).focus();
    await page.keyboard.press("Escape");
    await page.mouse.move(0, 0);
  }
});

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
  const sourceAck = page.waitForResponse(response => response.request().method() === "PUT"
    && new URL(response.url()).pathname === `/api/v2/projects/${id}/source-outline/source`);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  const savedSource = await json(await sourceAck);
  expect(savedSource.source.revision).toBe(1);
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const prepared = await json<Preparation>(request.post(`${base}/source-outline/candidates`));
  await writeDelivery(prepared, "outline", { source: "潮汐灯", episodes: [{ ep: 1, synopsis: "两次选择、三个结局与一个汇合点。" }] });
  await json(request.post(`${base}/source-outline/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${base}/source-outline/accept`, { data: { jobId: prepared.jobId, expectedSourceRevision: 1, expectedOutlineRevision: 0 } }));
  await page.reload();
  const map = page.getByTestId("section-map");
  const suggestion = page.getByRole("region", { name: "助手剧情分支建议" });
  const prepareSuggestion = async () => {
    const response = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v2/projects/${id}/branch-suggestions` && response.request().method() === "POST");
    await suggestion.getByRole("button", { name: "准备剧情分支建议" }).click();
    return json(await response);
  };
  const state = await prepareSuggestion();
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
  const old = await prepareSuggestion();
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=brief`));
  await page.getByLabel("不同结局的数量", { exact: true }).fill("2");
  await page.getByLabel("故事梗概").fill("只调整简报，保留来源正文。");
  for (const width of [1920, 1440, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    const help = page.getByLabel("说明：每次完整播放的选择次数", { exact: true });
    await help.focus();
    const tooltip = page.getByRole("tooltip").filter({ hasText: "不是每次选择的选项数量" });
    await expect(tooltip).toBeVisible();
    await page.keyboard.press("Escape");
    await help.click();
    await expect(tooltip).toBeVisible();
    const endingHelp = page.getByLabel("说明：不同结局的数量", { exact: true });
    await endingHelp.click();
    await expect(endingHelp).toHaveAttribute("aria-expanded", "true");
    await help.focus();
    await expect(tooltip).toBeVisible();
    await expect(endingHelp).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByRole("tooltip")).toHaveCount(1);
    await help.click();
    await expect(tooltip).toBeVisible();
    await expect(page.getByRole("tooltip")).toHaveCount(1);
    const bounds = await tooltip.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: info.outputPath(`brief-${width}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await page.getByRole("button", { name: "确认并保存目标", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=brief`));
  await page.getByRole("button", { name: "返回来源与大纲" }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue(retained.source.material.text);
  await expect(map).toContainText("需要重新检查");
  expect((await request.get(`${base}/branch-suggestions/${old.candidate.jobId}/draft`)).ok()).toBe(false);
  await suggestion.getByRole("button", { name: "放弃此建议任务" }).click();
  const fresh = await prepareSuggestion();
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
