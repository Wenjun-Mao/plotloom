import { expect, test } from "./fixture";
import { createScriptProject, endpoint } from "./f5a-fixture";

test("changed F5A Brief authority has a readable protected diagnostic at desktop and narrow widths", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "brief-style-diagnostic");
  const diagnostic = { code: "binding_value_changed", owner: "storyboard-review", field: "storyboard_render_contract", technicalMessage: "storyboard render contract changed" };
  await page.route(`**${new URL(endpoint(workbench.apiOrigin, id)).pathname}`, route => route.fulfill({ contentType: "application/json", body: JSON.stringify({
    status: "stale", candidate: null, acceptedReview: null, staleReasons: [diagnostic], acceptedReviewState: { status: "missing", staleReasons: [] },
  }) }));
  const dispatches: string[] = [];
  page.on("request", observed => { if (observed.method() === "POST" && /\/(?:send|pipeline-runs|start)$/.test(new URL(observed.url()).pathname)) dispatches.push(observed.url()); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const notice = page.getByTestId("storyboard-review").locator(":scope > .review-context-notice");
  await expect(notice.locator("details")).not.toHaveAttribute("open", "");
  await notice.getByText("查看创作依据的技术详情", { exact: true }).click();
  for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 600 }]) {
    await page.setViewportSize(size);
    await expect(notice.getByText("分镜视觉方向与审核要求已变化，需要重新检查这份内容。", { exact: true })).toBeVisible();
    await expect(notice).not.toContainText("undefined");
    const link = notice.getByRole("link", { name: "在新页打开分镜评审" });
    await expect(link).toHaveAttribute("href", `?project=${id}&stage=source#storyboard-review`);
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(notice.locator("details")).toHaveAttribute("open", "");
    await expect(notice).toContainText("storyboard_render_contract");
    await expect(notice).toContainText(diagnostic.technicalMessage);
    await notice.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`f5-brief-diagnostic-${size.width}x${size.height}.png`) });
    expect(dispatches).toEqual([]);
  }
});
