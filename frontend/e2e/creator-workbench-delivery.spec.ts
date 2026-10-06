import { execFileSync } from "node:child_process";
import path from "node:path";
import { checkedStaticTest as test, expect } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";

test("checked bundle delivers a clean isolated nine-node example without admitting or dispatching it", async ({ page, request, workbench }, info) => {
  const id = await createCreatorGraph(request, workbench.apiOrigin, "final-clean-example");
  const url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const before = await json(request.get(`${url}/graph-workbench`));
  expect(before.draft.payload.mapping.topology.nodes).toHaveLength(9);
  expect(before.draft.payload.mapping.topology.edges).toHaveLength(9);
  const failures: string[] = [], writes: string[] = [];
  page.on("pageerror", error => failures.push(error.message));
  page.on("requestfailed", request => { if (/\.(js|css)(\?|$)/.test(request.url())) failures.push(request.url()); });
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(`${request.method()} ${request.url()}`); });
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.getByRole("button", { name: "选择节点 风暴前的共同开场", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("tab", { name: "故事", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("风暴前的共同开场");
  expect(await page.locator(".creator-structure-check").getAttribute("open")).toBeNull();
  expect(await page.evaluate(() => scrollY)).toBe(0);
  expect(await page.getByLabel("剧情图横向平移", { exact: true }).evaluate(element => element.scrollLeft)).toBe(0);
  await page.screenshot({ path: info.outputPath("clean-example-1280-viewport.png") });
  await page.reload();
  await expect(page.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("风暴前的共同开场");
  expect(await json(request.get(`${url}/graph-workbench`))).toEqual(before);
  const source = await json(request.get(`${url}/source-outline`));
  expect(source.graphAdmission).toBeNull(); expect(source.acceptedSectionMap).toBeNull();
  expect((await json(request.get(`${url}/runs`))).runs).toEqual([]);
  expect(writes).toEqual([]); expect(failures).toEqual([]);
});

for (const viewport of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) test(`checked production controls remain reachable ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot, "--seconds", "2.5", "--repeat-scenes"], { cwd: path.resolve(".."), encoding: "utf8" }).trim();
  const bridge = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/production-bridge`));
  const cut = bridge.proposal.cuts.filter((cut: { sectionId: string; sceneIndex: number }) => cut.sectionId === "opening" && cut.sceneIndex === 2).at(-1);
  const failures: string[] = [], writes: string[] = [];
  page.on("pageerror", error => failures.push(error.message));
  page.on("requestfailed", request => { if (/\.(js|css)(\?|$)/.test(request.url())) failures.push(request.url()); });
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(`${request.method()} ${request.url()}`); });
  await page.setViewportSize(viewport);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  const action = page.locator(`[data-production-shot="${cut.shotId}"]`).getByRole("button", { name: "镜头审核与媒体", exact: true });
  await expect(action).toBeEnabled();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await action.scrollIntoViewIfNeeded();
    const inspector = (await page.getByRole("complementary", { name: "当前节点详情" }).boundingBox())!;
    expect(inspector.y).toBeGreaterThanOrEqual(50); expect(inspector.y + inspector.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator("html").evaluate(element => getComputedStyle(element).colorScheme)).toBe("dark");
    await page.screenshot({ path: info.outputPath(`production-${colorScheme}-preference-viewport.png`) });
  }
  await action.focus(); await page.keyboard.press("Enter");
  await expect(page.getByTestId("shot-preparation-summary")).toContainText(`当前镜头准备状态 · ${cut.shotId}`);
  await page.screenshot({ path: info.outputPath("shot-owner-viewport.png") });
  expect(writes).toEqual([]); expect(failures).toEqual([]);
});
