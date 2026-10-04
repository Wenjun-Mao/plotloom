import { expect, test } from "./fixture";
import { readFile } from "node:fs/promises";
import path from "node:path";

test("unchanged original synopsis confirms without direction and freezes existing Brief settings", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  const synopsis = "许宁在小院决定放飞纸飞机，或把它收好后离开。";
  await page.getByLabel("片名").fill("风里的纸飞机");
  await page.getByLabel("故事梗概").fill(synopsis);
  await page.getByLabel("类型", { exact: true }).fill("生活短片");
  await page.getByLabel("视觉风格").fill("真人写实，柔和自然光");
  await page.getByLabel("目标游玩时长（秒）").fill("30");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project creation did not bind an ID");
  await expect(page.getByLabel("故事内容")).toHaveValue(synopsis);
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("");
  await expect(page.getByText("已从项目简报带入故事梗概。可直接使用，也可按需补充细节。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  const saved = await (await request.get(`${base}/source-outline`)).json();
  expect(saved.source.material).toMatchObject({ text: synopsis, adaptationIntent: "" });
  expect(saved.candidate).toBeNull();
  expect(saved.acceptedOutline).toBeNull();

  const prepare = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/source-outline/candidates`);
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  const response = await prepare;
  expect(response.ok()).toBeTruthy();
  const prepared = await response.json();
  const frozen = JSON.parse(await readFile(path.join(prepared.packagePath, "request.json"), "utf8"));
  const { title, synopsis: briefSynopsis, ...settings } = (await (await request.get(base)).json()).brief;
  expect(title).toBe("风里的纸飞机");
  expect(briefSynopsis).toBe(synopsis);
  expect(frozen.source.text).toBe(synopsis);
  expect(frozen.source.adaptationIntent).toBe("");
  expect(frozen.inputArtifacts["outline-settings.json"]).toEqual(settings);
  expect(JSON.parse(await readFile(path.join(prepared.packagePath, "inputs", "outline-settings.json"), "utf8"))).toEqual(settings);
  expect(settings).toMatchObject({ targetPlaythroughSeconds: 30, genre: "生活短片", visualStyle: "真人写实，柔和自然光" });
  expect((await (await request.get(`${base}/source-outline`)).json()).acceptedOutline).toBeNull();
});

test("source type changes retain writing and require a goal only for imported material", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一个有两种告别方式的故事。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const save = page.getByRole("button", { name: "确认改编内容" });
  await expect(save).toBeEnabled();
  for (const kind of ["imported_text", "existing_work"]) {
    await page.getByLabel("来源类型").selectOption(kind);
    await expect(page.getByLabel("改编目标")).toHaveAttribute("aria-required", "true");
    await expect(save).toBeDisabled();
    await expect(page.getByText("请填写改编目标，说明如何将原作改编成互动短片。", { exact: true })).toBeVisible();
  }
  await page.getByLabel("故事内容").fill("保留这个尚未确认的故事草稿。");
  await page.getByLabel("改编目标").fill("保持原作人物，把两个结局展开为动作。");
  await expect(save).toBeEnabled();
  await page.getByLabel("来源类型").selectOption("synopsis");
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("保持原作人物，把两个结局展开为动作。");
  await expect(page.getByLabel("补充创作要求（可选）")).not.toHaveAttribute("aria-required", "true");
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("保留这个尚未确认的故事草稿。");
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("保持原作人物，把两个结局展开为动作。");
});
