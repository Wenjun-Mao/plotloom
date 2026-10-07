import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "./fixture";
import { changeScript, createScriptProject, fixture, hash, json, writeDelivery } from "./f5a-fixture";

test("archived Script static reading reveals long scenes and keeps scripts isolated", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "static-script-report", {}, ["cast", "art"]);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}/script`;
  const prepared = await json(request.post(`${root}/candidates`));
  const script = await fixture("script.json");
  await writeDelivery(prepared, "script", script);
  // The report fixture deliberately has long content, independently of timing
  // admission for the technical candidate; it cannot qualify creative linkage.
  const longScript = structuredClone(script);
  const scene = longScript.episodes[0].scenes[0];
  const speaker = scene.characters[0];
  scene.flow.push(...Array.from({ length: 60 }, () => ({ action: "Long archived scene line." })));
  scene.flow.push({ action: "Final archived scene." });
  scene.flow.push(...Array.from({ length: 30 }, () => ({ speaker, line: "Archived dialogue." })));
  const reportSourcePath = path.join(path.dirname(prepared.deliveryPath), "long-report-source.json");
  await writeFile(reportSourcePath, JSON.stringify(longScript));
  const report = Buffer.concat([
    execFileSync(process.execPath, ["third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs", "render", reportSourcePath, "--html", "--lang", "en"], { cwd: path.resolve("..") }),
    // Deliberate report-only hostile fixture, never a live specialist claim.
    Buffer.from(`<script>parent.document.body.dataset.archiveMutation="bad";</script><script>fetch("https://report-security.invalid/probe");</script><script>window.archiveExecuted=true;</script><button id="unsafe-action" onclick="fetch('https://report-security.invalid/click')">Hostile fixture action</button>`),
  ]);
  await writeDelivery(prepared, "script", script, report);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${root}/accept`, { data: { jobId: prepared.jobId, expectedScriptRevision: 0, binding: prepared.binding } }));
  const archiveUrl = `${root}/candidates/${prepared.jobId}/report`;
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  const projected = await request.get(`${archiveUrl}?presentation=static`);
  expect(projected.headers()["content-security-policy"]).toBe("sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;");
  let attemptedNetwork = 0;
  page.on("request", r => { if (r.url().includes("report-security.invalid")) attemptedNetwork++; });
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const panel = page.getByTestId("script-review");
  await panel.getByText("打开上游报告（静态阅读）", { exact: true }).click();
  await expect(panel).toContainText("静态阅读视图：所有场次与台词完整展开");
  const iframe = panel.locator("iframe");
  await expect(iframe).toHaveAttribute("sandbox", "");
  await expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");
  const frame = page.frameLocator('iframe[title="static derived upstream script report"]');
  await expect(frame.locator(".scenes.clip").first()).toContainText("Final archived scene.");
  const bounds = await frame.locator(".scenes.clip").first().evaluate(el => ({ height: el.clientHeight, scroll: el.scrollHeight }));
  expect(bounds.height).toBeGreaterThan(300);
  expect(bounds.height).toBe(bounds.scroll);
  expect(await frame.locator(".cast-lines").first().evaluate(el => el.clientHeight)).toBeGreaterThan(186);
  await expect(frame.locator(".cast-lines").first().locator("li").filter({ hasText: "Archived dialogue." })).toHaveCount(30);
  await expect(frame.locator(".cast-lines").first().locator("li").last()).toContainText("Come in safely.");
  for (const section of ["sec-timing", "sec-script", "sec-scenes", "sec-cast", "sec-gates"]) await expect(frame.locator(`#${section}`)).toBeVisible();
  for (const selector of [".scmore", ".copy", ".expo"]) for (const control of await frame.locator(selector).all()) await expect(control).toBeHidden();
  expect(await page.locator("body").getAttribute("data-archive-mutation")).toBeNull();
  expect(await frame.locator("body").evaluate(() => (window as unknown as { archiveExecuted?: boolean }).archiveExecuted)).toBeUndefined();
  await frame.locator("#unsafe-action").click();
  expect(attemptedNetwork).toBe(0);
  await panel.getByText("打开上游报告（静态阅读）", { exact: true }).click();
  await panel.getByText("打开上游报告（静态阅读）", { exact: true }).click();
  await expect(frame.locator(".scenes.clip").first()).toContainText("Final archived scene.");
  expect(await (await request.get(archiveUrl)).text()).toBe(report.toString());
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
  await changeScript(request, workbench.apiOrigin, id);
  const warnedArchive = await (await request.get(archiveUrl)).text();
  const warnedStatic = await (await request.get(`${archiveUrl}?presentation=static`)).text();
  expect(warnedArchive).toContain("does not describe the current accepted revision");
  expect(warnedStatic).toContain(warnedArchive);
  expect(hash(await readFile(path.join(prepared.deliveryPath, "report.html")))).toBe(hash(report));
});
