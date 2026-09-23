import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { demoProject } from "../src/demo";
import { StoryboardPage } from "../src/pages/StoryboardPage";

vi.mock("../src/features/media/ManagedMediaWorkbench", () => ({
  ManagedMediaWorkbench: ({ selectedShot }: { selectedShot?: { id: string } }) => createElement("div", { "data-testid": "selected-media-shot" }, selectedShot?.id ?? "none"),
}));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const render = async (entityId: string) => {
  await act(async () => root.render(createElement(StoryboardPage, {
    bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, value: demoProject.storyboard,
    stale: false, mediaTasks: {}, saving: false, entityId,
    onSave: async () => undefined,
  })));
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("selects the exact routed shot and refuses a no-longer-owned ID without falling back", async () => {
  const second = demoProject.storyboard.shots[1];
  await render(`shot:${second.id}`);
  expect(host.querySelector('[data-testid="selected-media-shot"]')?.textContent).toBe(second.id);
  expect((host.querySelector(".shot-inspector input") as HTMLInputElement | null)?.value).toBe(second.id);

  await render("shot:no-longer-owned");
  expect(host.querySelector('[data-testid="unknown-storyboard-entity"]')?.textContent).toContain("未打开其他镜头");
  expect(host.querySelector('[data-testid="selected-media-shot"]')?.textContent).toBe("none");
  expect(host.querySelector(".shot-inspector .section-title strong")?.textContent).toBe("选择镜头");
});
