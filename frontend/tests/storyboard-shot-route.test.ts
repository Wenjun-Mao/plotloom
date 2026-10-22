import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { demoProject } from "../src/demo";
import { StoryboardPage } from "../src/pages/StoryboardPage";

vi.mock("../src/features/media/ManagedMediaWorkbench", () => ({
  ManagedMediaWorkbench: ({ selectedShot, readOnly, lifecycleRevision }: { selectedShot?: { id: string }; readOnly: boolean; lifecycleRevision?: number }) => createElement("div", { "data-testid": "selected-media-shot", "data-read-only": readOnly, "data-lifecycle-revision": lifecycleRevision }, selectedShot?.id ?? "none"),
}));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const render = async (entityId: string, saving = false, readOnly = false, lifecycleRevision?: number) => {
  await act(async () => root.render(createElement(StoryboardPage, {
    bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, value: demoProject.storyboard,
    stale: false, mediaTasks: {}, saving, readOnly, entityId, lifecycleRevision,
    onSave: async () => undefined,
  })));
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it.each([
  [false, true, "保存分镜", true],
  [true, false, "正在保存…", true],
  [false, false, "保存分镜", false],
])("separates saving %s from read-only %s while retaining action locks", async (saving, readOnly, label, locked) => {
  await render(`shot:${demoProject.storyboard.shots[0].id}`, saving, readOnly);
  const save = host.querySelector<HTMLButtonElement>(".page-actions button")!;
  expect(save.textContent).toBe(label);
  expect(save.disabled).toBe(locked);
  expect(host.querySelector('[data-testid="selected-media-shot"]')?.getAttribute("data-read-only")).toBe(String(locked));
  if (locked) {
    await act(async () => host.querySelector<HTMLButtonElement>(".coverage-link button")!.click());
    expect(document.querySelector("dialog")).toBeNull();
  }
});

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

it("bounds card and inspector headings while preserving full authored fields", async () => {
  const value = structuredClone(demoProject.storyboard);
  const shot = value.shots[0];
  shot.title = "Long photographic composition. ".repeat(40);
  shot.composition = shot.title;
  shot.action = "阿岚伸手握住开关。";
  const original = JSON.stringify(value);
  const changed = vi.fn();
  await act(async () => root.render(createElement(StoryboardPage, {
    bible: demoProject.storyBible, graph: demoProject.storyGraph,
    sceneBeats: demoProject.sceneBeats, value, stale: false, mediaTasks: {},
    saving: false, readOnly: false, entityId: `shot:${shot.id}`,
    onSave: async () => undefined, onDraftChange: changed,
  })));
  expect(host.querySelector(".shot-copy strong")?.textContent).toBe(shot.action);
  expect(host.querySelector(".shot-inspector .section-title strong")?.textContent).toBe(shot.action);
  expect([...host.querySelectorAll<HTMLInputElement>(".shot-inspector input")].some(input => input.value === shot.title)).toBe(true);
  expect([...host.querySelectorAll<HTMLTextAreaElement>(".shot-inspector textarea")].some(input => input.value === shot.composition)).toBe(true);
  expect(changed).not.toHaveBeenCalled();
  expect(JSON.stringify(value)).toBe(original);
});

it("passes lifecycle revision to the media read owner without remounting the shot editor", async () => {
  const entity = `shot:${demoProject.storyboard.shots[0].id}`;
  await render(entity, false, false, 1);
  const editor = host.querySelector(".shot-inspector input");
  await render(entity, false, true, 2);
  expect(host.querySelector('[data-testid="selected-media-shot"]')?.getAttribute("data-lifecycle-revision")).toBe("2");
  expect(host.querySelector(".shot-inspector input")).toBe(editor);
  await render(entity, false, false, 3);
  expect(host.querySelector('[data-testid="selected-media-shot"]')?.getAttribute("data-lifecycle-revision")).toBe("3");
  expect(host.querySelector(".shot-inspector input")).toBe(editor);
});

it.each([
  ["migration", false, true], ["deletion", false, true],
  ["migration", true, false], ["deletion", true, false],
])("cancels pending %s when saving=%s or read-only=%s and never revives it", async (operation, saving, readOnly) => {
  const changed = vi.fn();
  const shot = demoProject.storyboard.shots[0];
  const renderState = async (isSaving: boolean, isReadOnly: boolean) => {
    await act(async () => root.render(createElement(StoryboardPage, {
      bible: demoProject.storyBible, graph: demoProject.storyGraph,
      sceneBeats: demoProject.sceneBeats, value: demoProject.storyboard,
      stale: false, mediaTasks: {}, saving: isSaving, readOnly: isReadOnly,
      entityId: `shot:${shot.id}`, onSave: async () => undefined, onDraftChange: changed,
    })));
  };
  await renderState(false, false);
  if (operation === "migration") {
    const target = demoProject.sceneBeats.scenes.find(scene => scene.id !== shot.sceneId)!;
    const select = host.querySelector<HTMLSelectElement>('[aria-label="迁移镜头到场景"]')!;
    await act(async () => { select.value = target.id; select.dispatchEvent(new Event("change", { bubbles: true })); });
  } else {
    await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "删除镜头")!.click());
  }
  const confirmation = `[data-testid="${operation === "migration" ? "shot-scene-migration-impact" : "shot-deletion-impact"}"]`;
  expect(host.querySelector(confirmation)).not.toBeNull();
  expect(changed).not.toHaveBeenCalled();
  await renderState(saving, readOnly);
  expect(host.querySelector(confirmation)).toBeNull();
  expect(changed).not.toHaveBeenCalled();
  await renderState(false, false);
  expect(host.querySelector(confirmation)).toBeNull();
  expect(changed).not.toHaveBeenCalled();
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
      value: demoProject.storyboard, stale: false, mediaTasks: {}, saving: false, readOnly: false,
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
