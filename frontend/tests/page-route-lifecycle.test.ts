import { describe, expect, it, vi } from "vitest";
import { usePageWithDrainedRoutes } from "../e2e/page-route-lifecycle";

describe("browser page route lifetime", () => {
  it("finishes the test body, then waits for its pending handlers", async () => {
    let release!: () => void;
    const pending = new Promise<void>(resolve => { release = resolve; });
    const page = { unrouteAll: vi.fn(() => pending) };
    const body = vi.fn(async current => { expect(current).toBe(page); });
    let finished = false;
    const lifecycle = usePageWithDrainedRoutes(page, body).then(() => { finished = true; });
    await Promise.resolve();
    expect(body).toHaveBeenCalledOnce();
    expect(page.unrouteAll).toHaveBeenCalledWith({ behavior: "wait" });
    expect(finished).toBe(false);
    release();
    await lifecycle;
    expect(finished).toBe(true);
  });

  it("drains after a failing test without suppressing its error", async () => {
    const error = new Error("test failure");
    const page = { unrouteAll: vi.fn(async () => {}) };
    await expect(usePageWithDrainedRoutes(page, async () => { throw error; })).rejects.toBe(error);
    expect(page.unrouteAll).toHaveBeenCalledWith({ behavior: "wait" });
  });

  it("does not suppress a route-drain failure", async () => {
    const error = new Error("route failure");
    const page = { unrouteAll: vi.fn(async () => { throw error; }) };
    await expect(usePageWithDrainedRoutes(page, async () => {})).rejects.toBe(error);
  });
});
