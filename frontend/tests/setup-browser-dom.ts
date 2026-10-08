import { beforeEach, vi } from "vitest";

// jsdom has no layout or native scroll implementation. Unit checks observe the
// requested scroll; the real-browser suite owns its visual/viewport outcome.
beforeEach(() => {
  if (typeof Element !== "undefined") Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true, writable: true, value: vi.fn(),
  });
});
