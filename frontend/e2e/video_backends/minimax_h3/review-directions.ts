import { expect, type Locator } from "@playwright/test";
import type { VideoJob } from "../../../src/types";

/** Browser fixture uses a synthetic native drafter/checker and offline H3.
 * This establishes transport/authority behavior, never live semantic fidelity. */
export async function freezeReviewedFixtureDirections(panel: Locator, apiOrigin: string, seed?: string): Promise<VideoJob> {
  const page = panel.page(), projectId = new URL(page.url()).searchParams.get("project")!;
  const root = `/api/v2/projects/${encodeURIComponent(projectId)}`;
  const currentResponse = await page.request.get(`${apiOrigin}${root}/video-batch`);
  expect(currentResponse.ok()).toBe(true);
  const current = await currentResponse.json();
  if (current && !["approved", "cancelled"].includes(current.state)) {
    // Each explicit fixture invocation requests a new single candidate. Settle
    // only its exact observed one-target predecessor, preserving existing media.
    expect(current.manifest.setup.singleRequest).toBeTruthy();
    expect(current.manifest.scopeShotIds).toHaveLength(1);
    const cancelled = await page.request.post(`${apiOrigin}${root}/video-batch/control`, { data: {
      batchId: current.id, expectedControlRevision: current.controlRevision, action: "cancel",
    } });
    expect(cancelled.ok(), await cancelled.text()).toBe(true);
  }
  const production = panel.locator("#video-production");
  if (!await production.evaluate(element => (element as HTMLDetailsElement).open)) await production.locator("summary").first().click();
  const review = panel.getByTestId("h3-directions-review");
  if (!await review.evaluate(element => (element as HTMLDetailsElement).open)) await review.locator("summary").first().click();
  const newTake = review.getByRole("button", { name: "保留设置并准备新的原片候选", exact: true });
  if (await newTake.isVisible()) await newTake.click();
  if (seed !== undefined) await review.getByLabel("H3 随机种子", { exact: true }).fill(seed);
  await review.getByRole("button", { name: "读取当前来源", exact: true }).click();
  if (await newTake.isVisible()) { await newTake.click(); await review.getByRole("button", { name: "读取当前来源", exact: true }).click(); }
  await review.getByRole("button", { name: "准备本镜头制作简报", exact: true }).click();
  const drafted = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `${root}/video-batch/draft`);
  await review.getByRole("button", { name: "用助手起草并独立检查指令", exact: true }).click();
  const draftedResponse = await drafted;
  expect(draftedResponse.ok(), await draftedResponse.text()).toBe(true);
  const authorize = review.getByRole("button", { name: "授权本镜头制作意图并开始生成", exact: true });
  await expect(authorize).toBeEnabled({ timeout: 30_000 });
  const prepared = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `${root}/video-jobs`);
  await authorize.click();
  const response = await prepared; expect(response.ok(), await response.text()).toBe(true);
  const created = await response.json() as VideoJob;
  let ingested: VideoJob | undefined;
  await expect.poll(async () => {
    const read = await page.request.get(`${apiOrigin}${root}/video-jobs`); expect(read.ok()).toBe(true);
    ingested = ((await read.json()) as { jobs: VideoJob[] }).jobs.find(job => job.id === created.id);
    return ingested?.state;
  }, { timeout: 30_000 }).toBe("ingested");
  await expect(panel.getByTestId(`video-job-player-${created.id}`)).toBeVisible({ timeout: 15_000 });
  return ingested!;
}
