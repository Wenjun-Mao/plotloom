import { beforeEach, vi } from "vitest";

// jsdom has no layout or native scroll implementation. Unit checks observe the
// requested scroll; the real-browser suite owns its visual/viewport outcome.
beforeEach(() => {
  if (typeof Element !== "undefined") Object.defineProperty(Element.prototype, "scrollIntoView", {
    configurable: true, writable: true, value: vi.fn(),
  });
  // jsdom does not implement native modal APIs. This shim models open state
  // only; keyboard containment, inertness and restoration require browser tests.
  if (typeof HTMLDialogElement !== "undefined") Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: { configurable: true, writable: true, value(this: HTMLDialogElement) { this.open = true; } },
    close: { configurable: true, writable: true, value(this: HTMLDialogElement) { this.open = false; } },
  });
});
