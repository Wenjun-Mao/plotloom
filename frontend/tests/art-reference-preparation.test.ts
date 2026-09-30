import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ArtReferenceGallery } from "../src/pages/ArtReferenceGallery";
import { defaultImageRequirements, studyStatus } from "../src/pages/artReferencePresentation";
import type { ArtReferenceProposal } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const art = { style: "live-action", scenes: [{ id: "S01", name: "车站", image: { prompt: "Live-action station", sheet: "Station sheet", negativePrompt: "people" } }, { id: "S02", name: "咖啡馆" }], props: [{ id: "P01", name: "手机" }] };
const defaults = { projectId: "project", art, acceptedRevision: 1, acceptedContentHash: "hash", studies: [] as ArtReferenceProposal[], decisions: [], decisionStates: [], readOnly: false, busy: false, setAssignment: vi.fn(), refresh: vi.fn(async () => {}) };
const study: ArtReferenceProposal = { id: "study", projectId: "project", subjectType: "scene", subjectId: "S01", state: "prepared", current: true, request: { frozenSnapshot: { renderDirection: "保留雨后积水，柔和晨光。", subject: { content: art.scenes[0] } } }, requestHash: "request", exportedAt: null, cancelledAt: null, cancellationReason: null, createdAt: "now", deliveries: [] };

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
async function render(overrides: Partial<typeof defaults> = {}) { await act(async () => root.render(createElement(ArtReferenceGallery, { ...defaults, ...overrides }))); }
function textarea() { return host.querySelector("textarea")!; }
async function edit(value: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(textarea(), value);
    textarea().dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function select(index: number) { await act(async () => (host.querySelectorAll(".reference-subjects button")[index] as HTMLButtonElement).click()); }

it.each([["live-action", "真人写实"], ["realistic", "半写实厚涂"], ["ghibli", "吉卜力动画"], ["unknown", "已接受的美术风格"]])("inherits %s with Chinese requirements", (style, label) => {
  expect(defaultImageRequirements(style, "scene")).toContain(label);
  expect(defaultImageRequirements(style, "scene")).toContain("不添加人物");
  expect(defaultImageRequirements(style, "prop")).toContain("白色背景，不添加人物或手");
  expect(defaultImageRequirements(style, "scene")).not.toMatch(/[A-Za-z]/);
});

it("keeps model instructions collapsed and preserves per-subject edits across refreshes", async () => {
  await render();
  expect(textarea().value).toContain("真人写实");
  expect(host.textContent).toContain("未准备");
  const advanced = host.querySelector("details")!;
  expect(advanced.open).toBe(false);
  expect(advanced.textContent).toContain("Live-action station");
  await edit("中文环境要求");
  await select(2);
  expect(textarea().value).toContain("白色背景");
  await edit("中文道具要求");
  await select(0);
  await render({ art: { ...art } });
  expect(textarea().value).toBe("中文环境要求");
  await select(2);
  expect(textarea().value).toBe("中文道具要求");
});

it.each([{ projectId: "other" }, { acceptedRevision: 2 }, { acceptedContentHash: "new-hash" }])("discards drafts when the accepted session changes: %j", async (change) => {
  await render(); await edit("旧草稿");
  await render(change);
  expect(textarea().value).toBe(defaultImageRequirements("live-action", "scene"));
  await render();
  expect(textarea().value).not.toBe("旧草稿");
});

it("submits Chinese unchanged and presents the prepared snapshot read-only", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareArtReferenceProposal").mockResolvedValue({ proposal: study });
  await render(); await edit("  保留雨后积水，柔和晨光。  ");
  await act(async () => [...host.querySelectorAll("button")].find((button) => button.textContent === "准备图片生成任务")!.click());
  expect(prepare).toHaveBeenCalledWith("project", { subjectType: "scene", subjectId: "S01", renderDirection: "保留雨后积水，柔和晨光。" });
  await render({ studies: [study] });
  expect(textarea().readOnly).toBe(true);
  expect(textarea().value).toBe("保留雨后积水，柔和晨光。");
  expect(host.textContent).toContain("待发送");
  expect(host.textContent).not.toContain("准备图片生成任务");
});

it("disables editing in read-only mode and uses current accepted prompts after stale/cancelled tasks", async () => {
  await render({ readOnly: true });
  expect(textarea().disabled).toBe(true);
  const changed = { ...study, current: false, request: { frozenSnapshot: { renderDirection: "Old overlay", subject: { content: { image: { prompt: "Old prompt" } } } } } };
  await render({ studies: [changed] });
  expect(textarea().readOnly).toBe(false);
  expect(host.querySelector("details")!.textContent).toContain("Live-action station");
  expect(host.querySelector("details")!.textContent).not.toContain("Old prompt");
  await render({ studies: [{ ...study, state: "cancelled", current: false }] });
  expect(host.textContent).toContain("准备图片生成任务");
});

it("labels task lifecycle without implying image acceptance", () => {
  expect(studyStatus(undefined)).toBe("未准备");
  expect(studyStatus(study)).toBe("待发送");
  expect(studyStatus({ ...study, state: "exported" })).toBe("等待图片");
  expect(studyStatus({ ...study, state: "delivered" })).toBe("图片已返回");
  expect(studyStatus({ ...study, current: false })).toBe("设定已变更");
  expect(studyStatus({ ...study, state: "cancelled", current: false })).toBe("已取消");
  expect(studyStatus({ ...study, deliveries: [{ state: "rejected" } as ArtReferenceProposal["deliveries"][number]] })).toBe("交付未通过检查");
});
