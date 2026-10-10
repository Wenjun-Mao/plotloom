import { expect, test } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";

for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
  test.describe(`read recovery ${viewport.width}x${viewport.height}`, () => {
    test.use({ viewport });
    test("initial graph failure and GET retry preserve canonical content in both modes", async ({ page, request, workbench }, testInfo) => {
      const id = await createScriptProject(request, workbench.apiOrigin, "read-recovery", {}, []);
      const url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
      const before = await json(request.get(url));
      const writes: string[] = [];
      page.on("request", req => { if (req.url().includes("/api/v2/") && req.method() !== "GET") writes.push(`${req.method()} ${req.url()}`); });
      let fail = true, holdRetry = false;
      let release!: () => void, held: Promise<void>;
      await page.route(`**/api/v2/projects/${id}/graph-workbench`, async route => {
        if (!fail) { if (holdRetry) await held; return route.continue(); }
        await held;
        await route.fulfill({ status: 503, json: { detail: "held graph read" } });
      });
      for (const mode of ["creator", "graph"]) {
        held = new Promise(done => { release = done; });
        await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=${mode}`);
        await expect(page.getByText("正在读取共享图草稿，请稍候。", { exact: false })).toBeVisible();
        await expect(page.getByRole("button", { name: "重新读取图草稿", exact: true })).toBeDisabled();
        await page.screenshot({ path: testInfo.outputPath(`${mode}-initial-waiting.png`), animations: "disabled" });
        release();
        await expect(page.getByRole("button", { name: "重新读取图草稿", exact: true })).toBeEnabled();
        await expect(page.getByText("读取成功后才能显示和编辑图草稿。", { exact: false })).toBeVisible();
        await expect(page.getByText("当前显示上次读取的内容", { exact: false })).toHaveCount(0);
        if (mode === "graph") {
          await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeDisabled();
          await expect(page.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
        }
        await page.screenshot({ path: testInfo.outputPath(`${mode}-initial-failed.png`), animations: "disabled" });
      }
      fail = false;
      holdRetry = true; held = new Promise(done => { release = done; });
      await page.getByRole("button", { name: "重新读取图草稿", exact: true }).click();
      await expect(page.getByRole("button", { name: "重新读取图草稿", exact: true })).toBeDisabled();
      await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeDisabled();
      await page.screenshot({ path: testInfo.outputPath("graph-retry-waiting.png"), animations: "disabled" });
      release();
      await expect(page.getByRole("button", { name: "保存图草稿", exact: true })).toBeEnabled();
      expect(writes).toEqual([]); expect(await json(request.get(url))).toEqual(before);
    });

    test("directory failed read offers GET retry and does not label absence as empty", async ({ page, workbench }, testInfo) => {
      let fail = true;
      let release!: () => void;
      let held = new Promise<void>(done => { release = done; });
      const writes: string[] = [];
      page.on("request", req => { if (req.url().includes("/api/v2/") && req.method() !== "GET") writes.push(req.method()); });
      await page.route("**/api/v2/projects?*", async route => { await held; return fail ? route.fulfill({ status: 503, json: { detail: "directory read failed" } }) : route.continue(); });
      await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
      await page.getByRole("button", { name: "打开项目目录", exact: true }).click();
      const dialog = page.getByRole("dialog", { name: "项目目录", exact: true });
      await expect(dialog.getByText("正在读取项目目录，请稍候。", { exact: true })).toBeVisible();
      await dialog.screenshot({ path: testInfo.outputPath("directory-initial-waiting.png"), animations: "disabled" });
      release();
      await expect(dialog.getByRole("button", { name: "重新读取项目目录", exact: true })).toBeEnabled();
      await expect(dialog.getByText("项目目录尚未读入，请重新读取。", { exact: true })).toBeVisible();
      await expect(dialog.getByText("还没有可用项目", { exact: true })).toHaveCount(0);
      await dialog.screenshot({ path: testInfo.outputPath("directory-initial-failed.png"), animations: "disabled" });
      fail = false;
      held = new Promise<void>(done => { release = done; });
      await dialog.getByRole("button", { name: "重新读取项目目录", exact: true }).click();
      await expect(dialog.getByText("正在读取项目目录，请稍候。", { exact: true })).toBeVisible();
      release();
      await expect(dialog.getByText("还没有可用项目", { exact: true })).toBeVisible();
      expect(writes).toEqual([]);
    });

    test("both graph modes retry Source failures using only GET and preserve graph content", async ({ page, request, workbench }, testInfo) => {
      const id = await createScriptProject(request, workbench.apiOrigin, "source-read-retry", {}, []);
      const graphUrl = `${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`;
      const before = await json(request.get(graphUrl));
      let fail = true;
      const writes: string[] = [];
      page.on("request", req => { if (req.url().includes("/api/v2/") && req.method() !== "GET") writes.push(req.method()); });
      await page.route(`**/api/v2/projects/${id}/source-outline`, route => fail ? route.fulfill({ status: 503, json: { detail: "Source read failed" } }) : route.continue());
      for (const mode of ["graph", "creator"]) {
        fail = true;
        await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=${mode}`);
        await expect(page.getByRole("button", { name: "重新读取来源与大纲", exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeDisabled();
        await expect(page.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
        await page.screenshot({ path: testInfo.outputPath(`${mode}-source-failed.png`), animations: "disabled" });
        // Keep delayed initial Source reads failing; only the explicit retry may recover.
        await page.waitForLoadState("networkidle");
        fail = false;
        await page.getByRole("button", { name: "重新读取来源与大纲", exact: true }).click();
        await expect(page.getByRole("button", { name: "重新读取来源与大纲", exact: true })).toHaveCount(0);
        await expect(page.getByRole("button", { name: "保存图草稿", exact: true })).toBeEnabled();
        if (mode === "graph") await expect(page.getByRole("button", { name: "确认图内容", exact: true })).toBeEnabled();
      }
      expect(writes).toEqual([]); expect(await json(request.get(graphUrl))).toEqual(before);
    });
  });
}
