import type { Locator } from "@playwright/test";

/** Open the row's management disclosure without accidentally toggling it shut. */
export async function openProjectManagement(row: Locator): Promise<void> {
  const more = row.getByRole("button", { name: /^更多 · / });
  if (await more.getAttribute("aria-expanded") !== "true") await more.click();
}
