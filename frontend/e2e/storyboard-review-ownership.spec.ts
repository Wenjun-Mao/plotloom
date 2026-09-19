import type { Page, Route, Request } from "@playwright/test";
import { expect, test } from "./fixture";
import { createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";

async function switchProject(page: Page, id: string): Promise<void> {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await directory.locator(`[data-project-id="${id}"] .directory-open`).click();
  await expect(directory).toBeHidden();
  await sourceStage(page);
}
async function sourceStage(page: Page): Promise<void> {
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 来源与大纲/ }).click();
}

for (const transition of ["A-B-A", "unmount"] as const) {
  for (const operation of ["load", "copy", "refresh"] as const) {
    for (const responseKind of ["success", "error"] as const) {
      test(`F5A ${transition} contains held ${operation} ${responseKind} after response settlement`, async ({ page, request, workbench }) => {
        test.setTimeout(90_000);
        const id = await createScriptProject(request, workbench.apiOrigin, `${transition}-${operation}-${responseKind}`);
        const other = transition === "A-B-A" ? await createScriptProject(request, workbench.apiOrigin, "other") : "";
        const root = endpoint(workbench.apiOrigin, id);
        const prepared = await json(request.post(`${root}/candidates`));
        if (operation === "refresh") await writeDelivery(prepared);
        let release!: () => void;
        let markStarted!: () => void;
        const held = new Promise<void>(resolve => { release = resolve; });
        const started = new Promise<void>(resolve => { markStarted = resolve; });
        const url = operation === "load" ? root : `${root}/candidates/${prepared.jobId}/${operation === "copy" ? "handoff" : "refresh"}`;
        const pathname = new URL(url).pathname;
        const pattern = `**${pathname}`;
        let captured = false;
        const routeHandler = async (route: Route) => {
          if (captured) return route.continue();
          captured = true;
          // Perform the real operation first, holding only the response delivery
          // to the old component. The new mount observes real settled state.
          const upstream = await route.fetch();
          markStarted();
          await held;
          if (responseKind === "error") await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: "held stale failure" }) });
          else await route.fulfill({ response: upstream });
        };
        if (operation !== "load") {
          await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`);
          await expect(page.getByTestId("storyboard-review")).toBeVisible();
        }
        await page.route(pattern, routeHandler);
        try {
          // Do not await a full navigation while its initial API load is
          // intentionally withheld below. On a slower runner, the app can
          // start that fetch before `goto` settles, which deadlocks the test
          // before it reaches `release`.
          const initialNavigation = operation === "load"
            ? page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source`, { waitUntil: "domcontentloaded" })
            : undefined;
          if (operation !== "load") {
            await page.getByTestId("storyboard-review").getByRole("button", {
              name: operation === "copy" ? "重新复制冻结 handoff" : "刷新 specialist delivery",
            }).click();
          }
          await started;
          await initialNavigation;
          if (transition === "A-B-A") { await switchProject(page, other); await switchProject(page, id); }
          else {
            await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /剧情 DAG/ }).click();
            await expect(page.getByTestId("storyboard-review")).toHaveCount(0);
          }
          if (transition === "A-B-A") await expect(page.getByTestId("storyboard-review")).toBeVisible();
          const refreshes: string[] = [];
          const observe = (request: Request) => { if (request.method() === "GET" && new URL(request.url()).pathname === new URL(root).pathname) refreshes.push(request.url()); };
          page.on("request", observe);
          const settled = page.waitForResponse(response => new URL(response.url()).pathname === pathname);
          release();
          const response = await settled;
          expect(response.status()).toBe(responseKind === "success" ? 200 : 409);
          expect(await response.finished()).toBeNull();
          await page.waitForLoadState("networkidle");
          page.off("request", observe);
          expect(refreshes).toEqual([]);
          if (transition === "unmount") await sourceStage(page);
          const panel = page.getByTestId("storyboard-review");
          await expect(panel).toBeVisible();
          await expect(panel.getByLabel("复制给 specialist 的冻结任务")).toHaveCount(0);
          await expect(panel.getByRole("alert")).toHaveCount(0);
          await expect(panel.getByRole("button").first()).toBeEnabled();
        } finally {
          release?.();
          await page.unroute(pattern, routeHandler);
        }
      });
    }
  }
}
