import type { Page } from "@playwright/test";

/** Exercise named creator controls, not historical sidebar or panel positions. */
export async function navigateToSecondaryTool(page: Page, label: string): Promise<void> {
  const navigation = page.getByRole("navigation", { name: "编辑与工具" });
  if (!await navigation.isVisible()) await page.getByText("编辑与工具", { exact: true }).click();
  // Quarantine appends a count to its accessible name; the authored label
  // remains an exact child, so navigation must not depend on that live count.
  await navigation.getByRole("button").filter({ has: page.getByText(label, { exact: true }) }).click();
}

export async function openMediaPreparation(page: Page): Promise<void> {
  await openMediaDisclosure(page, "准备与参考 · 图片、角色、导入");
}

export async function openMediaKeyframes(page: Page): Promise<void> {
  await openMediaDisclosure(page, "关键帧与静帧预览");
}

export async function openServiceStatus(page: Page): Promise<void> {
  await openTechnicalDisclosure(page, "details.topbar-technical-status");
}

export async function openTechnicalDetails(page: Page): Promise<void> {
  await openTechnicalDisclosure(page, "details.workspace-technical-details");
}

async function openTechnicalDisclosure(page: Page, selector: string): Promise<void> {
  const details = page.locator(selector);
  if (await details.getAttribute("open") === null) await details.locator(":scope > summary").click();
}

async function openMediaDisclosure(page: Page, label: string): Promise<void> {
  const details = page.locator("details.workbench-support").filter({
    has: page.getByText(label, { exact: true }),
  });
  if (await details.getAttribute("open") === null) await details.locator(":scope > summary").click();
}
