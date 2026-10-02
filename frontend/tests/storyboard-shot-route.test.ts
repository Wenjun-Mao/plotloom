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

it("confirms only the displayed coverage link and cancels without changing the draft", async () => {
  const originals = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  try {
    const link = demoProject.storyboard.shotBeatLinks[0];
    const changed = vi.fn();
    await act(async () => root.render(createElement(StoryboardPage, {
      bible: demoProject.storyBible, graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats,
      value: demoProject.storyboard, stale: false, mediaTasks: {}, saving: false,
      entityId: `shot:${link.shotId}`, onSave: async () => undefined, onDraftChange: changed,
    })));
    const remove = host.querySelector<HTMLButtonElement>(".coverage-link button")!;
    changed.mockClear(); await act(async () => remove.click());
    expect(document.querySelector("dialog")!.textContent).toContain(link.beatId);
    expect(changed).not.toHaveBeenCalled();
    await act(async () => document.querySelector("dialog")!.querySelector<HTMLButtonElement>("button")!.click());
    expect(changed).not.toHaveBeenCalled();
    await act(async () => remove.click());
    await act(async () => document.querySelector("dialog")!.querySelectorAll<HTMLButtonElement>("button")[1].click());
    expect(changed).toHaveBeenCalledOnce();
    expect(changed.mock.calls[0][0].shotBeatLinks).toEqual(demoProject.storyboard.shotBeatLinks.filter(item => item.shotId !== link.shotId || item.beatId !== link.beatId));
  } finally {
    ["showModal", "close"].forEach((name, index) => { if (originals[index]) Object.defineProperty(HTMLDialogElement.prototype, name, originals[index]!); else Reflect.deleteProperty(HTMLDialogElement.prototype, name); });
  }
});
