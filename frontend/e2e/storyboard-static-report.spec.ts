import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { createScriptProject, endpoint, fixture, hash, json, writeDelivery } from "./f5a-fixture";

test("pinned Storyboard static reader reveals long segments/prompts without permissions or archive rewrites", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "static-storyboard-report");
  const root = endpoint(workbench.apiOrigin, id);
  const prepared = await json(request.post(`${root}/candidates`));
  const board = await fixture("storyboard.json");
  // Report-only geometry fixture: the admitted technical candidate remains its
  // validated source-bound fixture; this long report is not a live delivery claim.
  const longBoard = structuredClone(board);
  const segment = longBoard.episodes[0].segments[0];
  longBoard.episodes[0].segments = Array.from({ length: 30 }, (_, i) => ({
    ...structuredClone(segment), id: `LONG_SEGMENT_${i + 1}`,
    h3Prompt: `${"Long archived prompt. ".repeat(100)}Final prompt ${i + 1}.`,
  }));
  const renderer = path.resolve("../third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs");
  const scriptPath = path.join(prepared.packagePath, "inputs/script.json");
  const render = (images: boolean) => execFileSync(process.execPath, ["--input-type=module", "-e",
    `import {renderHtml} from ${JSON.stringify(renderer)};import fs from 'node:fs';const board=${JSON.stringify(longBoard)};const script=JSON.parse(fs.readFileSync(${JSON.stringify(scriptPath)},'utf8'));process.stdout.write(renderHtml(board,{script,lang:'en',imageExists:()=>${images}}));`]);
  const report = Buffer.concat([render(false), Buffer.from('<script>window.storyboardExecuted=true;</script><script>try{parent.document.body.dataset.storyboardMutation="bad"}catch{}</script><script>fetch("https://report-security.invalid/board")</script>')]);
  await writeDelivery(prepared, "storyboard", board, report);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
  const archiveUrl = `${root}/candidates/${prepared.jobId}/report`;
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  let network = 0;
  page.on("request", r => { if (r.url().includes("report-security.invalid")) network++; });
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const panel = page.getByTestId("storyboard-review");
  await panel.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
  await expect(panel).toContainText("所有分段与提示词完整展开");
  const iframe = panel.locator("iframe");
  await expect(iframe).toHaveAttribute("sandbox", "");
  await expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");
  const frame = panel.frameLocator("iframe");
  await expect(frame.locator("#seg-LONG_SEGMENT_30")).toContainText("Final prompt 30.");
  const geometry = await frame.locator(".shots.clip").first().evaluate(e => ({ height: e.clientHeight, scroll: e.scrollHeight }));
  expect(geometry.height).toBeGreaterThan(760);
  expect(geometry.height).toBe(geometry.scroll);
  expect(await frame.locator(".pp").first().evaluate(e => e.clientHeight === e.scrollHeight)).toBe(true);
  await expect(frame.locator(".fprompt").first()).not.toBeEmpty();
  for (const section of ["sec-rhythm", "sec-segments", "sec-batches", "sec-dialogue", "sec-gates"]) await expect(frame.locator(`#${section}`)).toBeVisible();
  for (const selector of [".expo", ".copy", ".shmore", ".lightbox"]) for (const control of await frame.locator(selector).all()) await expect(control).toBeHidden();
  expect(await frame.locator("body").evaluate(() => (window as unknown as { storyboardExecuted?: boolean }).storyboardExecuted)).toBeUndefined();
  expect(await page.locator("body").getAttribute("data-storyboard-mutation")).toBeNull();
  expect(network).toBe(0);
  await panel.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
  await panel.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
  await expect(frame.locator("#seg-LONG_SEGMENT_30")).toBeVisible();
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());

  // Exercise the pinned renderer's real all-images branch independently. Its
  // relative URIs remain unchanged and deliberately blocked by data-only CSP.
  const imageReport = render(true).toString();
  await page.route(`**/storyboard-source-review/candidates/${prepared.jobId}/report?presentation=static`, async route => {
    const response = await route.fetch();
    const style = (await response.text()).slice(report.toString().length);
    await route.fulfill({ response, body: imageReport + style });
  });
  await page.reload();
  await panel.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
  await expect(frame.locator("img.frame").first()).toHaveAttribute("src", "LONG_SEGMENT_1/f1.png");
  await expect(frame.locator("img.frame").first()).toHaveCSS("cursor", "default");
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
});
