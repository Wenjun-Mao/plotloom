import type { Page } from "@playwright/test";

/** Route work belongs to the page fixture, not its disposed request context. */
export async function usePageWithDrainedRoutes<T extends Pick<Page, "unrouteAll">>(
  page: T,
  use: (page: T) => Promise<void>,
): Promise<void> {
  try {
    await use(page);
  } finally {
    await page.unrouteAll({ behavior: "wait" });
  }
}
