import { expect, test } from "./fixture";
import { createAcceptedCastOnlyProject } from "./fixtures/cast-reference";

test("explicitly edits all cast image directions, cancels safely, and freezes the new reference context", async ({ page, request, workbench }) => {
  const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "image-direction");
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  // Seed this test's existing conflicting directions through the supported
  // edit API; shared cast fixtures keep their existing contract.
  const initial = await getJson<any>(request.get(`${endpoint}/cast`));
  await getJson(request.post(`${endpoint}/cast/reopen`, {
    data: { expectedCastRevision: initial.acceptedCast.revision },
  }));
  const painterly = {
    style: "Painterly illustration", prompt: "Painted beacon keeper portrait.",
    promptLocal: "绘画风格的灯塔守护者。", negativePrompt: "photograph, watermark",
    sheet: "Painted identity sheet.", tags: ["painterly", "illustration"],
  };
  const seededCast = structuredClone(initial.acceptedCast.cast);
  seededCast.characters[0].image = painterly;
  await getJson(request.post(`${endpoint}/cast/save`, {
    data: {
      expectedCastRevision: initial.acceptedCast.revision, binding: initial.acceptedCast.binding,
      cast: seededCast, consumerMappings: initial.acceptedCast.consumerMappings,
    },
  }));
  const baseline = await getJson<any>(request.get(`${endpoint}/cast`));
  expect(baseline.acceptedCast.cast).toEqual(seededCast);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
  const panel = page.getByTestId("cast-review");
  await panel.getByRole("button", { name: "编辑角色设定" }).click();
  await panel.getByText("角色图像方向", { exact: true }).click();
  await expect(panel.getByLabel("角色图像风格", { exact: true })).toHaveValue(painterly.style);
  await panel.getByLabel("角色图像风格", { exact: true }).fill("Unsaved direction");
  await panel.getByRole("button", { name: "取消编辑" }).click();
  expect((await getJson<any>(request.get(`${endpoint}/cast`))).acceptedCast).toEqual(baseline.acceptedCast);

  await panel.getByRole("button", { name: "编辑角色设定" }).click();
  await panel.getByText("角色图像方向", { exact: true }).click();
  await expect(panel.getByLabel("角色图像风格", { exact: true })).toHaveValue(painterly.style);
  await expect(panel.getByLabel("角色图像提示词", { exact: true })).toHaveValue(painterly.prompt);
  const labels = {
    style: "角色图像风格", prompt: "角色图像提示词", promptLocal: "角色图像中文提示词",
    negativePrompt: "角色图像反向提示词", sheet: "角色设定图提示词",
  };
  const directions = {
    style: "Live-action photographic direction", prompt: "Photographic portrait; preserve the cast identity.",
    promptLocal: "真人写实；保留角色身份。", negativePrompt: "painting, cartoon, watermark",
    sheet: "Photographic sheet with consistent orthographic identity views.", tags: ["live-action", "photographic"],
  };
  for (const [key, label] of Object.entries(labels)) await panel.getByLabel(label, { exact: true }).fill(directions[key as keyof typeof labels]);
  await panel.getByLabel("角色图像标签（每行一个）", { exact: true }).fill(directions.tags.join("\n"));
  expect((await getJson<any>(request.get(`${endpoint}/cast`))).acceptedCast).toEqual(baseline.acceptedCast);
  const saving = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/cast/save`);
  await panel.getByRole("button", { name: "保存角色修改" }).click();
  expect((await saving).ok()).toBeTruthy();
  await page.reload();
  await expect(panel).toContainText(directions.style);
  const saved = await getJson<any>(request.get(`${endpoint}/cast`));
  expect(saved.acceptedCast.revision).toBe(baseline.acceptedCast.revision + 1);
  expect(saved.acceptedCast.consumerMappings).toEqual(baseline.acceptedCast.consumerMappings);
  const expected = structuredClone(baseline.acceptedCast.cast);
  expected.characters[0].image = { ...expected.characters[0].image, ...directions };
  expect(saved.acceptedCast.cast).toEqual(expected);

  const gallery = page.getByTestId("character-reference-gallery");
  await gallery.getByLabel("想法").fill("Explicit new photographic reference");
  await gallery.getByRole("button", { name: "创建提案" }).click();
  await expect(gallery.getByRole("button", { name: "发送给图像生成助手" })).toBeEnabled();
  const proposals = await getJson<any>(request.get(`${endpoint}/character-reference-proposals`));
  expect(proposals.proposals[0].request.frozenSnapshot.acceptedCast.image).toEqual(directions);
});

async function getJson<T>(response: Promise<import("@playwright/test").APIResponse>): Promise<T> {
 const result = await response;
 expect(result.ok(), await result.text()).toBeTruthy();
 return result.json() as Promise<T>;
}
