import { afterEach, expect, it, vi } from "vitest";
import { workspaceViewportTop } from "../src/app/workspace/workspaceViewport";

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); });
function header(className: string, top: number, bottom: number, width = 1000) {
  const element = document.createElement("section"); element.className = className;
  vi.spyOn(element, "getBoundingClientRect").mockReturnValue({ top, bottom, width, height: bottom - top } as DOMRect);
  document.body.append(element); return element;
}
it("reserves both toolbar and changing workflow guide height", () => {
  header("topbar", 0, 58);
  const guide = header("recommended-workflow-guide", 58, 124);
  expect(workspaceViewportTop()).toBe(124);
  vi.mocked(guide.getBoundingClientRect).mockReturnValue({ top: 58, bottom: 300, width: 1000, height: 242 } as DOMRect);
  expect(workspaceViewportTop()).toBe(300);
});
it("excludes hidden and scrolled-away chrome and bounds oversized chrome to the viewport", () => {
  header("topbar", -100, -42);
  header("recommended-workflow-guide", 58, 124, 0);
  expect(workspaceViewportTop()).toBe(0);
  header("recommended-workflow-guide", 58, window.innerHeight + 100);
  expect(workspaceViewportTop()).toBe(window.innerHeight);
});
