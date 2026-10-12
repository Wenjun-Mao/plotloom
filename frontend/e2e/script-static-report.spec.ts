import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { changeScript, createScriptProject, fixture, hash, json, writeDelivery } from "./f5a-fixture";
import { auditStaticReport } from "./static-report-audit";

test("Script content review stays readable and its original static report remains isolated", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "static-script-report", {}, ["cast", "art"]);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}/script`;
  const prepared = await json(request.post(`${root}/candidates`));
  const script = await fixture("script.json");
  const candidateScript = structuredClone(script);
  const scene = candidateScript.episodes[0].scenes[0];
  const speaker = scene.characters[0];
  scene.flow.push(
    { action: `米拉把粗糙的电缆平放在木桌上，再次核对灯塔与码头的供电标记。`.repeat(3) },
    { speaker, line: "安迪，如果我把电缆送到灯塔，我就要向灯塔供电。", delivery: "她压低声音，逐字确认取舍" },
  );
  // The report fixture deliberately has long content, independently of timing
  // admission for the technical candidate; it cannot qualify creative linkage.
  const longScript = structuredClone(candidateScript);
  const reportScene = longScript.episodes[0].scenes[0];
  reportScene.flow.push(...Array.from({ length: 60 }, () => ({ action: "Long archived scene line." })));
  reportScene.flow.push({ action: "Final archived scene." });
  reportScene.flow.push(...Array.from({ length: 30 }, () => ({ speaker, line: "Archived dialogue." })));
  await writeDelivery(prepared, "script", candidateScript);
  const reportSourcePath = path.join(path.dirname(prepared.deliveryPath), "long-report-source.json");
  await writeFile(reportSourcePath, JSON.stringify(longScript));
  const report = Buffer.concat([
    execFileSync(process.execPath, ["third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs", "render", reportSourcePath, "--html", "--lang", "en"], { cwd: path.resolve("..") }),
    // Deliberate report-only hostile fixture, never a live specialist claim.
    Buffer.from(`<script>parent.document.body.dataset.archiveMutation="bad";</script><script>fetch("https://report-security.invalid/probe");</script><script>window.archiveExecuted=true;</script><button id="unsafe-action" onclick="fetch('https://report-security.invalid/click')">Hostile fixture action</button>`),
  ]);
  await writeDelivery(prepared, "script", candidateScript, report);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
  const archiveUrl = `${root}/candidates/${prepared.jobId}/report`;
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  const projected = await request.get(`${archiveUrl}?presentation=static`);
  expect(projected.headers()["content-security-policy"]).toBe("sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;");
  let attemptedNetwork = 0;
  page.on("request", r => { if (r.url().includes("report-security.invalid")) attemptedNetwork++; });

  // Reading a ready candidate, expanding its technical disclosure and
  // changing only the viewport must not mutate accepted review state.
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const panel = page.getByTestId("script-review");
  const writes: string[] = [];
  const recordWrite = (pending: import("@playwright/test").Request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(pending.method())) writes.push(`${pending.method()} ${pending.url()}`);
  };
  page.on("request", recordWrite);
  const candidateReview = panel.getByLabel("待审阅候选剧本 · 未确认", { exact: true });
  await expect(candidateReview).toContainText("候选状态：ready");
  await expect(candidateReview).toContainText("米拉把粗糙的电缆平放在木桌上");
  await expect(candidateReview).toContainText("keeper：安迪，如果我把电缆送到灯塔");
  await expect(candidateReview).toContainText("她压低声音，逐字确认取舍");
  for (const size of [{ width: 1280, height: 460 }, { width: 1280, height: 768 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await candidateReview.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    expect(await candidateReview.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    const name = `script-candidate-${size.width}x${size.height}.png`;
    const screenshot = await page.screenshot({ path: info.outputPath(name) });
    if (process.env.PLOTLOOM_E2E_SCREENSHOT_DIR) {
      const screenshotPath = path.join(process.env.PLOTLOOM_E2E_SCREENSHOT_DIR, name);
      await mkdir(path.dirname(screenshotPath), { recursive: true });
      await writeFile(screenshotPath, screenshot);
    }
  }
  const rawDisclosure = candidateReview.locator("details").filter({ hasText: "查看此对象的冻结绑定与完整原始剧本 JSON" });
  await rawDisclosure.locator(":scope > summary").click();
  await expect(rawDisclosure.locator("pre").nth(0)).toContainText('"sectionId": "opening"');
  await expect(rawDisclosure.locator("pre").nth(1)).toContainText("安迪，如果我把电缆");
  expect(writes).toEqual([]);
  page.off("request", recordWrite);

  await json(request.post(`${root}/accept`, { data: { jobId: prepared.jobId, expectedScriptRevision: 0, binding: prepared.binding } }));
  await page.reload();
  await expect(panel.getByLabel("当前已确认剧本 r1", { exact: true })).toContainText("米拉把粗糙的电缆平放在木桌上");
  await page.setViewportSize({ width: 1280, height: 768 });
  await panel.getByText("阅读原始剧本报告（只读）", { exact: true }).click();
  await expect(panel).toContainText("场次与台词已完整展开");
  const iframe = panel.locator("iframe");
  await expect(iframe).toHaveAttribute("sandbox", "");
  await expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");
  const frame = page.frameLocator('iframe[title="原始剧本交付报告（只读）"]');
  await expect(frame.locator(".scenes.clip").first()).toContainText("Final archived scene.");
  const bounds = await frame.locator(".scenes.clip").first().evaluate(el => ({ height: el.clientHeight, scroll: el.scrollHeight }));
  expect(bounds.height).toBeGreaterThan(300);
  expect(bounds.height).toBe(bounds.scroll);
  expect(await frame.locator(".cast-lines").first().evaluate(el => el.clientHeight)).toBeGreaterThan(186);
  await expect(frame.locator(".cast-lines").first().locator("li").filter({ hasText: "Archived dialogue." })).toHaveCount(30);
  await expect(frame.locator(".cast-lines").first().locator("li").last()).toContainText("Come in safely.");
  for (const section of ["sec-timing", "sec-script", "sec-scenes", "sec-cast", "sec-gates"]) await expect(frame.locator(`#${section}`)).toBeVisible();
  for (const section of ["sec-script", "sec-cast"]) await expect(frame.locator(`#${section} > .sec-h > .note`)).toBeHidden();
  for (const section of ["sec-timing", "sec-scenes"]) await expect(frame.locator(`#${section} > .sec-h > .note`)).toBeVisible();
  for (const selector of [".scmore", ".copy", ".expo"]) for (const control of await frame.locator(selector).all()) await expect(control).toBeHidden();
  await auditStaticReport(page, panel, "script", test.info());
  expect(await page.locator("body").getAttribute("data-archive-mutation")).toBeNull();
  expect(await frame.locator("body").evaluate(() => (window as unknown as { archiveExecuted?: boolean }).archiveExecuted)).toBeUndefined();
  await frame.locator("#unsafe-action").click();
  expect(attemptedNetwork).toBe(0);
  await panel.getByText("阅读原始剧本报告（只读）", { exact: true }).click();
  await panel.getByText("阅读原始剧本报告（只读）", { exact: true }).click();
  await expect(frame.locator(".scenes.clip").first()).toContainText("Final archived scene.");
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
  await changeScript(request, workbench.apiOrigin, id);
  const warnedArchive = await (await request.get(archiveUrl)).text();
  const warnedStatic = await (await request.get(`${archiveUrl}?presentation=static`)).text();
  expect(warnedArchive).toContain("does not describe the current accepted revision");
  expect(warnedStatic).toContain(warnedArchive);
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
  await page.reload();
  await expect(panel.getByLabel("当前已确认剧本 r2", { exact: true })).toContainText("Deterministic edited route status");
});
