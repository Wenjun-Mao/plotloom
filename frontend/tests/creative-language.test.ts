import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { canonicalBriefTitle, creativeDefaults } from "../src/creative-language";
import { applicationLanguage } from "../src/application-language";
import { demoProject } from "../src/demo";
import { addBibleEntity } from "../src/bible-editor";
import { addBeat, addCue, addScene } from "../src/scene-beats-editor";
import { createShot } from "../src/storyboard-editor";
import { DirectionPresets, genreGroups, visualGroups } from "../src/pages/DirectionPresets";
import { BriefPage } from "../src/pages/BriefPage";
import { ArtContentReview } from "../src/pages/ArtContentReview";
import { StoryboardReviewInspection } from "../src/pages/StoryboardReviewInspection";
import { OutlineReader } from "../src/pages/OutlineReader";
import { TracePage } from "../src/pages/TracePage";
import { ErrorNotice } from "../src/components";

const host = document.createElement("div");
let root = createRoot(host);
afterEach(async () => { await act(async () => root.unmount()); host.replaceChildren(); root = createRoot(host); vi.restoreAllMocks(); });

it.each(["zh-CN", "en-US"])("creates only new creative defaults in %s, preserving authored originals", language => {
  const original = structuredClone(demoProject), defaults = creativeDefaults(language);
  const bible = addBibleEntity(original.storyBible, "character", "new", language);
  expect(bible.characters.at(-1)?.name).toBe(defaults.entity);
  expect(bible.characters.slice(0, -1)).toEqual(original.storyBible.characters);
  const scenes = addScene(original.sceneBeats, () => "new-scene", "opening", language);
  expect(scenes.scenes.at(-1)?.title).toBe(defaults.scene);
  const beats = addBeat(scenes, "new-scene", () => "new-beat");
  const cues = addCue(beats, "new-beat", () => "new-cue", language);
  expect(cues.dialogueCues.at(-1)).toMatchObject({ voiceOver: defaults.narrator, language });
  const shot = createShot("new-shot", "new-scene", 1, scenes.scenes.at(-1)!, language);
  expect(shot).toMatchObject({ title: defaults.shot, cameraAngle: defaults.cameraAngle, cameraMovement: defaults.cameraMovement, transition: defaults.transition });
  expect(canonicalBriefTitle("", language)).toBe(defaults.title);
  expect(canonicalBriefTitle("已保存原文", language)).toBe("已保存原文");
  expect(original).toEqual(demoProject);
  expect(applicationLanguage.locale).toBe("zh-CN");
});

it("uses recovered English Brief language for empty titles while keeping interface and preset identities Chinese", async () => {
  const value = { ...demoProject.brief, language: "en-US", title: "", synopsis: "A choice at dawn.", genreSelections: [{ group: "subject" as const, value: "科幻" }] };
  const save = vi.fn(async () => undefined);
  await act(async () => root.render(createElement(BriefPage, { value, hasSavedProject: false, saving: false, onSave: save })));
  expect(host.textContent).toContain("项目简报");
  expect(host.textContent).toContain("英语");
  expect(host.querySelector('option[value="en-US"]')?.textContent).toBe("英语");
  expect(host.querySelector('button[aria-label="移除科幻"]')).toBeTruthy();
  await act(async () => [...host.querySelectorAll("button")].find(button => button.textContent === "确认项目简报")!.click());
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ title: "Untitled story", language: "en-US", genreSelections: value.genreSelections }));
  expect(value.title).toBe("");
});

it("retains an unsupported old locale without relabeling it or crashing Brief readback", async () => {
  await act(async () => root.render(createElement(BriefPage, { value: { ...demoProject.brief, language: "fr", title: "" }, hasSavedProject: true, saving: false, onSave: vi.fn() })));
  expect(host.textContent).toContain("原项目语言：fr");
  expect([...host.querySelectorAll("button")].find(button => button.textContent === "应用修改")?.disabled).toBe(true);
  expect(canonicalBriefTitle("", "fr")).toBe("");
});

it("shows authored descriptions first and keeps provider text in technical details without writing source", async () => {
  const art = { scenes: [{ id: "room", name: "Room", summary: "A quiet room.", lighting: [{ name: "Dawn", description: "Soft blue light.", prompt: "English provider render." }] }], props: [] };
  const cut = { seconds: 3, size: "MS", camera: "static", composition: "她望向窗外。", frame: "Provider image directions.", beats: [1], characters: [], props: [] };
  const before = JSON.stringify({ art, cut });
  await act(async () => root.render(createElement("div", null, createElement(ArtContentReview, { art }), createElement(StoryboardReviewInspection, { title: "分镜评审", value: { episodes: [{ ep: 1, segments: [{ id: "seg", cuts: [cut] }] }] } }))));
  expect(host.textContent).toContain("Soft blue light.");
  expect(host.textContent).toContain("她望向窗外。");
  expect(host.textContent).toContain("中景 · 固定 · 节拍");
  expect(host.querySelector("pre")?.closest("details")?.open).toBe(false);
  expect(JSON.stringify({ art, cut })).toBe(before);
});

it("offers a Chinese next action and lossless technical detail for raw provider failures", async () => {
  await act(async () => root.render(createElement(ErrorNotice, { message: "Connection refused: EHOSTUNREACH" })));
  expect(host.textContent).toContain("请检查当前操作");
  expect(host.querySelector("details pre")?.textContent).toBe("Connection refused: EHOSTUNREACH");
});


it("keeps unknown schema keys and original English event diagnostics in technical details", async () => {
  const event = { id: "event", at: "now", stage: "story_bible" as const, kind: "error" as const, title: "Connection refused", detail: "Exact transport reason", status: "error" as const };
  await act(async () => root.render(createElement("div", null,
    createElement(OutlineReader, { outline: { source: "Authored title", customField: "Authored value" } }),
    createElement(TracePage, { trace: [event], running: false, onRun: vi.fn(), onResume: vi.fn(), onCancel: vi.fn() }))));
  expect(host.querySelector(".outline-reader-section h4")?.textContent).toBe("技术字段");
  expect(host.querySelector(".outline-reader-section details code")?.textContent).toBe("customField");
  expect(host.querySelector(".outline-reader-section details")?.textContent).toContain("Authored value");
  expect(host.querySelector(".trace-event strong")?.textContent).not.toBe(event.title);
  expect(host.querySelector(".prompt-inspector details")?.textContent).toContain(event.title);
});


it("uses stable preset group identity rather than a translated display label for visual guidance", async () => {
  const props = { selections: [], detail: "", disabled: false, onSelections: vi.fn(), onDetail: vi.fn() };
  await act(async () => root.render(createElement(DirectionPresets, { ...props, label: "新的显示名称", groups: visualGroups })));
  expect(host.textContent).toContain("建议明确主要表现形式");
  await act(async () => root.render(createElement(DirectionPresets, { ...props, label: "视觉风格", groups: genreGroups })));
  expect(host.textContent).not.toContain("建议明确主要表现形式");
  expect(visualGroups[0].id).toBe("representation");
  expect(visualGroups[0].values).toEqual(["真人写实", "2D 动画", "3D 动画"]);
});
