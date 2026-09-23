import type { Page, Request } from "@playwright/test";
import { checkedStaticTest as test, expect } from "./fixture";

type AssetKind = "script" | "stylesheet";
type AssetLoad = "initial" | "reload";
type AssetResponse = {
  url: string;
  kind: AssetKind;
  status: number;
  load: AssetLoad;
  requestHeaders: Record<string, string>;
};

test("serves and persists the checked production bundle through FastAPI", async ({ page, workbench }) => {
  const assets = observeStaticPage(page, workbench.apiOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).waitFor();
  await expect(page.locator('script[src^="/v2/"]').first()).toHaveAttribute("src", /\.(?:m?js)$/);
  await expect(page.locator('link[rel="stylesheet"][href^="/v2/"]').first()).toHaveAttribute("href", /\.css$/);
  await page.getByRole("button", { name: "打开示例项目" }).click();

  const title = "E2E checked static bundle persistence";
  await page.getByLabel("片名").fill(title);
  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "保存简报" }).click();
  expect((await created).ok()).toBeTruthy();
  await expect(page).toHaveURL(/[?&]project=/);
  await expect(page.getByLabel("片名")).toHaveValue(title);

  assets.beginReload();
  await page.reload();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await expect(page.getByLabel("片名")).toHaveValue(title);
  await assets.assertHealthy();
});

test("the static smoke gate rejects a missing JavaScript or CSS response", async ({ context, workbench }) => {
  for (const missingPath of ["/v2/workbench.js", "/v2/workbench.css"]) {
    const page = await context.newPage();
    const assets = observeStaticPage(page, workbench.apiOrigin);
    await page.route((url) => url.origin === workbench.apiOrigin && url.pathname === missingPath,
      (route) => route.fulfill({
        status: 404,
        contentType: missingPath.endsWith(".css") ? "text/css" : "text/javascript",
        body: "counterfactual missing shipped asset",
      }));

    await page.goto(`${workbench.frontendOrigin}/v2/`);
    let failure: Error | undefined;
    try {
      await assets.assertHealthy();
    } catch (error) {
      failure = error instanceof Error ? error : new Error(String(error));
    }
    expect(failure?.message).toContain(`${missingPath} returned HTTP 404`);
    await page.close();
  }
});

function observeStaticPage(page: Page, apiOrigin: string) {
  const responses: Promise<AssetResponse>[] = [];
  const failedRequests: string[] = [];
  const pageErrors: string[] = [];
  let currentLoad: AssetLoad = "initial";

  // Attach every observer before navigation so modulepreloads and stylesheets
  // declared by index.html are part of the same shipped-bundle evidence.
  page.on("response", (response) => {
    const request = response.request();
    const kind = staticAssetKind(request, apiOrigin);
    if (!kind) return;
    const load = currentLoad;
    responses.push((async () => ({
      url: response.url(),
      kind,
      status: response.status(),
      load,
      requestHeaders: await request.allHeaders(),
    }))());
  });
  page.on("requestfailed", (request) => {
    if (staticAssetKind(request, apiOrigin)) {
      failedRequests.push(`${request.url()}: ${request.failure()?.errorText ?? "request failed"}`);
    }
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  return {
    beginReload() { currentLoad = "reload"; },
    async assertHealthy() {
      const assets = await Promise.all(responses);
      const successfulByUrl = new Set<string>();
      const invalidResponses: string[] = [];
      for (const asset of assets) {
        if (asset.status >= 200 && asset.status < 300) {
          successfulByUrl.add(asset.url);
          continue;
        }
        const headers = asset.requestHeaders;
        const conditionalRequest = Boolean(headers["if-none-match"] || headers["if-modified-since"]);
        if (asset.status === 304 && asset.load === "reload" && conditionalRequest && successfulByUrl.has(asset.url)) {
          continue;
        }
        invalidResponses.push(`${new URL(asset.url).pathname} returned HTTP ${asset.status}`);
      }

      if (invalidResponses.length) throw new Error(invalidResponses.join("; "));
      if (failedRequests.length) throw new Error(`static asset request failures: ${failedRequests.join("; ")}`);
      if (pageErrors.length) throw new Error(`browser page errors: ${pageErrors.join("; ")}`);
      if (!assets.some((asset) => asset.kind === "script" && asset.status >= 200 && asset.status < 300)) {
        throw new Error("no same-origin /v2 JavaScript asset completed successfully");
      }
      if (!assets.some((asset) => asset.kind === "stylesheet" && asset.status >= 200 && asset.status < 300)) {
        throw new Error("no same-origin /v2 stylesheet completed successfully");
      }
    },
  };
}

function staticAssetKind(request: Request, apiOrigin: string): AssetKind | undefined {
  const url = new URL(request.url());
  if (url.origin !== apiOrigin || !url.pathname.startsWith("/v2/")) return undefined;
  if (request.resourceType() === "script" || /\.(?:m?js)$/i.test(url.pathname)) return "script";
  if (request.resourceType() === "stylesheet" || /\.css$/i.test(url.pathname)) return "stylesheet";
  return undefined;
}
