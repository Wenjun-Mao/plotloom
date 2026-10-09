import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { expect, test, checkedStaticTest } from "./fixture";
import { createScriptProject, fixture, hash, json, writeDelivery } from "./f5a-fixture";
import { captureReportFramePoint, captureReportParagraphEnd, captureReportPoint, reportDesktopViewports } from "./static-report-audit";

for (const [width, height] of reportDesktopViewports) {
test(`pinned multi-character static reader retains all roles, relations, long synopsis, prompts and images ${width}x${height}`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "static-cast-report", {}, []);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}/cast`;
  const prepared = await json(request.post(`${root}/candidates`, { data: { renderStyle: "realistic" } }));
  // Actual pinned example + renderer, report-only fixture; not a live multi-role
  // delivery or source-binding claim for the admitted one-character candidate.
  const example = JSON.parse(await readFile(path.resolve("../third_party/shuohao-skills/skills/novel-characters/examples/渡口-cast.json"), "utf8"));
  const summary = `${"Long synopsis 中文 & <safe>. ".repeat(70)}Final synopsis line.`;
  const image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNn0AAAAASUVORK5CYII=";
  example.characters[0].sheetImage = image;
  example.characters[0].image.prompt += ` ${"Long prompt. ".repeat(80)}Final prompt line.`;
  const renderer = path.resolve("../third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs");
  const report = Buffer.concat([execFileSync(process.execPath, ["--input-type=module", "-e",
    `import {renderHtml} from ${JSON.stringify(renderer)};process.stdout.write(renderHtml(${JSON.stringify(example.characters)},'Pinned multi-role fixture',${JSON.stringify(summary)},'en',null,${JSON.stringify(example.style)}));`]),
    Buffer.from('<script>window.castExecuted=true;</script><script>try{parent.document.body.dataset.castMutation="bad"}catch{}</script><script>fetch("https://report-security.invalid/cast")</script>')]);
  await writeDelivery(prepared, "characters", await fixture("cast.json"), report);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
  const archiveUrl = `${root}/candidates/${prepared.jobId}/report`;
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  let network = 0;
  const writes: string[] = [];
  page.on("request", r => { if (r.url().includes("/api/v2/") && !["GET", "HEAD"].includes(r.method())) writes.push(`${r.method()} ${r.url()}`); });
  page.on("request", r => { if (r.url().includes("report-security.invalid")) network++; });
  const stateBeforeReading = await json(request.get(root));
  await page.setViewportSize({ width, height });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const panel = page.getByTestId("cast-review");
  const disclosure = panel.getByText("查看提案来源与技术详情", { exact: true });
  await captureReportPoint(page, disclosure, test.info(), "cast-disclosure-closed");
  await disclosure.click();
  await expect(panel).toContainText("角色报告静态阅读：全部角色、关系与提示词展开");
  await expect(panel.locator("iframe")).toHaveAttribute("sandbox", "");
  await expect(panel.locator("iframe")).toHaveAttribute("referrerpolicy", "no-referrer");
  await captureReportPoint(page, panel.getByText("角色报告静态阅读：全部角色、关系与提示词展开", { exact: false }), test.info(), "cast-reading-guidance");
  const frame = panel.frameLocator("iframe");
  await expect(frame.locator(".char")).toHaveCount(4);
  for (const character of example.characters) await expect(frame.locator(".char").filter({ has: frame.locator("h2", { hasText: character.name }) })).toBeVisible();
  await expect(frame.locator(".synopsis")).toContainText("Final synopsis line.");
  expect(await frame.locator(".synopsis p").evaluate(e => e.clientHeight === e.scrollHeight)).toBe(true);
  await captureReportParagraphEnd(page, panel.locator("iframe"), frame.locator(".synopsis p"), test.info(), "cast-synopsis-end");
  // The pinned desktop sidebar has a fixed viewport height above1080px.
  // Static linear reading must release it, not overlap subsequent role cards.
  if (width === 1700) {
  expect(await panel.locator("iframe").evaluate(e => e.clientWidth)).toBeGreaterThan(1080);
  const contentBounds = () => frame.locator(".side").evaluate(e => ({
    contentBottom: Math.max(...[...e.querySelectorAll(".synopsis p, footer")].map(content => content.getBoundingClientRect().bottom)),
    mainTop: e.nextElementSibling!.getBoundingClientRect().top,
  }));
  // Counterfactual pinned desktop height: the content, not merely the sidebar
  // box, must overlap main before the owning static height reset.
  await frame.locator(".side").evaluate(e => (e as HTMLElement).style.setProperty("height", "calc(100vh - var(--top))", "important"));
  const clipped = await contentBounds();
  expect(clipped.contentBottom).toBeGreaterThan(clipped.mainTop);
  await frame.locator(".side").evaluate(e => (e as HTMLElement).style.removeProperty("height"));
  const expanded = await contentBounds();
  expect(expanded.contentBottom).toBeLessThanOrEqual(expanded.mainTop);
  }
  for (let index = 0; index < example.characters.length; index++) {
    await captureReportFramePoint(page, panel.locator("iframe"), frame.locator(".char").nth(index).locator("h2"), test.info(), `cast-role-${index + 1}`);
  }
  await captureReportFramePoint(page, panel.locator("iframe"), frame.locator(".rel-n").first(), test.info(), "cast-role-relationship");
  await expect(frame.locator(".graph")).toBeVisible();
  await expect(frame.locator(".graph-h .hint")).toBeHidden();
  await expect(frame.locator(".graph-canvas")).toHaveAttribute("inert", "");
  for (const row of await frame.locator("button.grow").all()) { await expect(row).toBeDisabled(); await expect(row).not.toBeEmpty(); }
  await captureReportFramePoint(page, panel.locator("iframe"), frame.locator(".graph-h h2"), test.info(), "cast-relations");
  await expect(frame.locator(".pr p").filter({ hasText: "Final prompt line." })).toBeVisible();
  const prompt = frame.locator("details.pr").first();
  await expect(prompt).toHaveAttribute("open", "");
  await captureReportParagraphEnd(page, panel.locator("iframe"), prompt.locator("p"), test.info(), "cast-prompt-end");
  await prompt.locator("summary").click(); await expect(prompt.locator("p")).toBeHidden();
  await captureReportFramePoint(page, panel.locator("iframe"), prompt.locator("summary"), test.info(), "cast-prompt-closed");
  await prompt.locator("summary").click(); await expect(prompt.locator("p")).toBeVisible();
  await captureReportParagraphEnd(page, panel.locator("iframe"), prompt.locator("p"), test.info(), "cast-prompt-reopened");
  for (const selector of [".search", ".expo", ".copy", ".copy-img", ".syn-more", ".gtoggle", ".glabtoggle", ".roster", ".lightbox"]) for (const control of await frame.locator(selector).all()) await expect(control).toBeHidden();
  await expect(frame.locator("button.zoom")).toBeDisabled();
  await expect(frame.locator("button.zoom img")).toHaveAttribute("src", image);
  await expect(frame.locator("button.zoom img")).toBeVisible();
  await captureReportFramePoint(page, panel.locator("iframe"), frame.locator(".plate-c").first(), test.info(), "cast-image-caption");
  expect(await frame.locator("body").evaluate(() => (window as unknown as { castExecuted?: boolean }).castExecuted)).toBeUndefined();
  expect(await page.locator("body").getAttribute("data-cast-mutation")).toBeNull();
  expect(network).toBe(0);
  await disclosure.click();
  await disclosure.click();
  await expect(frame.locator(".char").last()).toBeVisible();
  await captureReportFramePoint(page, panel.locator("iframe"), frame.locator(".char").last().locator("h2"), test.info(), "cast-report-reopened");
  expect(await frame.locator("html").evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect(writes).toEqual([]);
  expect(await json(request.get(root))).toEqual(stateBeforeReading);
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
});

checkedStaticTest(`accepted Cast keeps its original report through reopen and edit, with a divergence notice ${width}x${height}`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "accepted-static-cast-report", {}, []);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}/cast`;
  const prepared = await json(request.post(`${root}/candidates`, { data: { renderStyle: "realistic" } }));
  const deliveredCast = await fixture("cast.json");
  const report = Buffer.from("<!doctype html><html><body><p>Original delivered Cast report marker.</p></body></html>");
  await writeDelivery(prepared, "characters", deliveredCast, report);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));

  let reportRequests = 0;
  page.on("request", current => {
    if (new URL(current.url()).pathname.endsWith("/report")) reportRequests++;
  });
  await page.setViewportSize({ width, height });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  const panel = page.getByTestId("cast-review");
  await panel.getByRole("button", { name: "确认使用此角色设定" }).click();
  await expect(panel).toContainText("已确认角色设定 r1");
  const acceptedState = await json(request.get(root));
  expect(acceptedState.acceptedCast.candidateJobId).toBe(prepared.jobId);
  const acceptedReport = panel.locator("details.cast-accepted-report");
  await expect(acceptedReport).toHaveCount(1);
  expect(acceptedState.acceptedCast.reportAvailable).toBe(true);
  expect(acceptedState.acceptedCast.differsFromDelivery).toBe(false);
  let observing = true;
  const readingWrites: string[] = [];
  page.on("request", current => { if (observing && current.url().includes("/api/v2/") && !["GET", "HEAD"].includes(current.method())) readingWrites.push(`${current.method()} ${current.url()}`); });
  await captureReportPoint(page, acceptedReport.locator("summary"), checkedStaticTest.info(), "cast-accepted-disclosure");

  await acceptedReport.locator("summary").click();
  await expect(acceptedReport.locator("iframe")).toHaveAttribute("sandbox", "");
  await expect(acceptedReport.locator("iframe")).toHaveAttribute("referrerpolicy", "no-referrer");
  const frame = acceptedReport.frameLocator("iframe");
  await expect(frame.locator("body")).toContainText("Original delivered Cast report marker.");
  await expect(acceptedReport).not.toContainText("当前已确认角色设定与交付内容不同");
  await captureReportPoint(page, acceptedReport.locator(".action-prerequisite"), checkedStaticTest.info(), "cast-accepted-guidance");
  await captureReportFramePoint(page, acceptedReport.locator("iframe"), frame.locator("p"), checkedStaticTest.info(), "cast-accepted-original");
  expect((await json(request.get(root))).acceptedCast).toEqual(acceptedState.acceptedCast);

  observing = false; // The following reopen/edit/save is explicit disposable setup.
  await panel.getByRole("button", { name: "编辑角色设定" }).click();
  await expect(panel.getByLabel("外观")).toBeVisible();
  await expect(frame.locator("body")).toContainText("Original delivered Cast report marker.");
  await panel.getByLabel("外观").fill("Changed after the original delivery.");
  await expect(frame.locator("body")).toContainText("Original delivered Cast report marker.");
  await expect(acceptedReport).not.toContainText("当前已确认角色设定与交付内容不同");
  await panel.getByRole("button", { name: "保存角色修改" }).click();
  await expect(panel).toContainText("已确认角色设定 r2");
  await expect(acceptedReport).toContainText("当前已确认角色设定与交付内容不同");
  await expect(frame.locator("body")).toContainText("Original delivered Cast report marker.");
  const savedState = await json(request.get(root));
  expect(savedState.acceptedCast.differsFromDelivery).toBe(true);
  observing = true;
  await captureReportPoint(page, acceptedReport.getByRole("note"), checkedStaticTest.info(), "cast-edited-divergence");
  await captureReportFramePoint(page, acceptedReport.locator("iframe"), frame.locator("p"), checkedStaticTest.info(), "cast-edited-original");
  expect((await json(request.get(root))).acceptedCast).toEqual(savedState.acceptedCast);
  expect(readingWrites).toEqual([]);
  expect(await (await request.get(`${root}/candidates/${prepared.jobId}/report`)).text()).toBe(report.toString());

  const requestsBeforeMissingReport = reportRequests;
  await page.route(`**/api/v2/projects/${id}/cast`, async route => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const state = await response.json();
    state.acceptedCast.reportAvailable = false;
    await route.fulfill({ response, body: JSON.stringify(state) });
  });
  await page.reload();
  await expect(panel.locator("details.cast-accepted-report")).toHaveCount(0);
  await expect(panel).not.toContainText("当前已确认角色设定与交付内容不同");
  expect(reportRequests).toBe(requestsBeforeMissingReport);
});
}
