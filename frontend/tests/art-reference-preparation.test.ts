import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { specialistsApi } from "../src/features/specialists/api";
import { ArtReferenceGallery } from "../src/pages/ArtReferenceGallery";
import { defaultImageRequirements, studyStatus } from "../src/pages/artReferencePresentation";
import type { ArtReferenceProposal } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const art = { style: "live-action", scenes: [{ id: "S01", name: "车站", image: { prompt: "Live-action station", sheet: "Station sheet", negativePrompt: "people" } }, { id: "S02", name: "咖啡馆" }], props: [{ id: "P01", name: "手机" }] };
const defaults = { projectId: "project", art, acceptedRevision: 1, acceptedContentHash: "hash", acceptedArtCurrent: true, studies: [] as ArtReferenceProposal[], decisions: [], decisionStates: [], readOnly: false, busy: false, setAssignment: vi.fn(), refresh: vi.fn(async () => {}) };
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

it("reconciles a queued send warning without hiding it or offering another send", async () => {
  const warning = "任务已入队，但无法确认助手聊天已打开。请勿重复发送。";
  const send = vi.spyOn(specialistsApi, "sendArtImage").mockRejectedValue(new Error(warning));
  const refresh = vi.fn(async () => { root.render(createElement(ArtReferenceGallery, { ...defaults, studies: [{ ...study, state: "exported", exportedAt: "now" }], refresh })); });
  await render({ studies: [study], refresh });
  await act(async () => [...host.querySelectorAll("button")].find((button) => button.textContent === "发送给图像生成助手")!.click());
  expect(send).toHaveBeenCalledTimes(1);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(host.textContent).toContain(warning);
  expect(host.textContent).toContain("检查图像交付");
  expect([...host.querySelectorAll("button")].some((button) => button.textContent === "发送给图像生成助手")).toBe(false);
});

it("does not reconcile a failed send into a different accepted session", async () => {
  let reject!: (error: Error) => void;
  vi.spyOn(specialistsApi, "sendArtImage").mockReturnValue(new Promise((_, fail) => { reject = fail; }));
  const refresh = vi.fn(async () => {});
  await render({ studies: [study], refresh });
  await act(async () => [...host.querySelectorAll("button")].find((button) => button.textContent === "发送给图像生成助手")!.click());
  await render({ acceptedRevision: 2, refresh });
  await act(async () => reject(new Error("Old session queue warning")));
  expect(refresh).not.toHaveBeenCalled();
  expect(host.textContent).not.toContain("Old session queue warning");
});

const delivered = { ...study, state: "delivered" as const };
const button = (label: string) => [...host.querySelectorAll("button")].find((entry) => entry.textContent === label);
async function click(label: string) { await act(async () => button(label)!.click()); }

it("opens and cancels a new draft without editing the frozen request or calling an API", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareArtReferenceProposal");
  const send = vi.spyOn(specialistsApi, "sendArtImage");
  const cancel = vi.spyOn(plotloomApi, "cancelArtReferenceProposal");
  await render({ studies: [delivered] });
  await click("修改要求，再生成一张");
  expect(textarea().readOnly).toBe(false);
  expect(textarea().value).toBe("保留雨后积水，柔和晨光。");
  expect(host.textContent).toContain("不会把旧图作为编辑输入");
  await edit("更低的视角，保持真人写实。");
  await click("取消本次修改");
  expect(textarea().readOnly).toBe(true);
  expect(textarea().value).toBe("保留雨后积水，柔和晨光。");
  expect(prepare).not.toHaveBeenCalled();
  expect(send).not.toHaveBeenCalled();
  expect(cancel).not.toHaveBeenCalled();
});

it("prepares a separate frozen candidate and still requires an explicit send", async () => {
  const next = { ...study, id: "new-study", request: { frozenSnapshot: { renderDirection: "新要求" } } };
  const prepare = vi.spyOn(plotloomApi, "prepareArtReferenceProposal").mockResolvedValue({ proposal: next });
  const send = vi.spyOn(specialistsApi, "sendArtImage").mockResolvedValue({} as never);
  const refresh = vi.fn(async () => root.render(createElement(ArtReferenceGallery, { ...defaults, studies: [next, delivered], refresh })));
  await render({ studies: [delivered], refresh });
  await click("修改要求，再生成一张");
  await edit("  新要求  ");
  await click("准备新图片任务");
  expect(prepare).toHaveBeenCalledExactlyOnceWith("project", { subjectType: "scene", subjectId: "S01", renderDirection: "新要求" });
  expect(send).not.toHaveBeenCalled();
  expect(textarea().readOnly).toBe(true);
  expect(textarea().value).toBe("新要求");
  expect(button("修改要求，再生成一张")).toBeUndefined();
  await click("发送给图像生成助手");
  expect(send).toHaveBeenCalledExactlyOnceWith("project", "new-study");
  expect(delivered.request.frozenSnapshot).toEqual(study.request.frozenSnapshot);
});

it("keeps retry drafts separate for scenes and props across navigation and refresh", async () => {
  const prop = { ...delivered, id: "prop-study", subjectType: "prop" as const, subjectId: "P01" };
  await render({ studies: [delivered, prop] });
  await click("修改要求，再生成一张"); await edit("环境新要求");
  await select(2); await click("修改要求，再生成一张"); await edit("道具新要求");
  await select(0);
  expect(textarea().value).toBe("环境新要求");
  expect(button("准备新图片任务")).toBeDefined();
  await render({ studies: [{ ...delivered }, prop] });
  expect(textarea().value).toBe("环境新要求");
  await select(2);
  expect(textarea().value).toBe("道具新要求");
});

it.each([{ projectId: "other" }, { acceptedRevision: 2 }, { acceptedContentHash: "new-hash" }])("does not carry revision mode across accepted sessions: %j", async (change) => {
  await render({ studies: [delivered] });
  await click("修改要求，再生成一张"); await edit("旧会话修改");
  await render({ studies: [delivered], ...change });
  expect(button("准备新图片任务")).toBeUndefined();
  expect(textarea().readOnly).toBe(true);
  await render({ studies: [delivered] });
  expect(button("准备新图片任务")).toBeUndefined();
});

it.each(["prepared", "exported", "cancelled"] as const)("does not offer another candidate for a %s task", async (state) => {
  await render({ studies: [{ ...study, state }] });
  expect(button("修改要求，再生成一张")).toBeUndefined();
});

it.each([{ readOnly: true }, { busy: true }])("disables revision controls when unavailable: %j", async (override) => {
  await render({ studies: [delivered], ...override });
  expect(button("修改要求，再生成一张")!.disabled).toBe(true);
});

it("retains revised requirements after a preparation failure and blocks blank drafts", async () => {
  vi.spyOn(plotloomApi, "prepareArtReferenceProposal").mockRejectedValue(new Error("Preparation failed"));
  await render({ studies: [delivered] });
  await click("修改要求，再生成一张"); await edit("   ");
  expect(button("准备新图片任务")!.disabled).toBe(true);
  await edit("保留本次修改"); await click("准备新图片任务");
  expect(host.textContent).toContain("Preparation failed");
  expect(textarea().readOnly).toBe(false);
  expect(textarea().value).toBe("保留本次修改");
});

it("blocks new image work for retained Art without hiding subjects or requirements", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareArtReferenceProposal");
  await render(); await edit("保留作者要求");
  await render({ acceptedArtCurrent: false });
  expect(textarea().value).toBe("保留作者要求");
  expect(textarea().disabled).toBe(true);
  expect(button("准备图片生成任务")!.disabled).toBe(true);
  expect(host.textContent).toContain("图片要求（暂不可编辑）");
  expect(host.textContent).toContain("当前只能查看已有图片要求；暂不能编辑或准备新图片任务。");
  expect(host.textContent).not.toContain("可以用中文补充构图");
  await click("准备图片生成任务");
  expect(prepare).not.toHaveBeenCalled();
  expect(host.textContent).toContain("暂不能准备、发送或选用参考图");
  expect(host.textContent).toContain("保留的美术主体");
  await select(2);
  expect(textarea().value).toContain("白色背景");
  await select(0);
  await render();
  expect(textarea().value).toBe("保留作者要求");
  expect(textarea().disabled).toBe(false);
  expect(host.textContent).toContain("可以用中文补充构图");
});

it("retains a revision draft through currentness loss and successful revalidation", async () => {
  await render({ studies: [delivered] });
  await click("修改要求，再生成一张"); await edit("保留环境新要求");
  await render({ acceptedArtCurrent: false, studies: [{ ...delivered, current: false }] });
  expect(textarea().value).toBe("保留环境新要求");
  expect(textarea().disabled).toBe(true);
  await render({ studies: [delivered] });
  expect(textarea().value).toBe("保留环境新要求");
  expect(textarea().disabled).toBe(false);
  expect(button("准备新图片任务")!.disabled).toBe(false);
  expect(delivered.request.frozenSnapshot).toEqual(study.request.frozenSnapshot);
});

it("cannot send or revise a retained task even if its proposal projection is current", async () => {
  const send = vi.spyOn(specialistsApi, "sendArtImage");
  await render({ acceptedArtCurrent: false, studies: [study] });
  expect(button("发送给图像生成助手")!.disabled).toBe(true);
  await click("发送给图像生成助手");
  expect(send).not.toHaveBeenCalled();
  await render({ acceptedArtCurrent: false, studies: [delivered] });
  expect(button("修改要求，再生成一张")!.disabled).toBe(true);
  await click("修改要求，再生成一张");
  expect(textarea().readOnly).toBe(true);
});

it.each(["prepared", "exported"] as const)("keeps cancellation available for a stale %s task", async (state) => {
  const cancel = vi.spyOn(plotloomApi, "cancelArtReferenceProposal").mockResolvedValue({ ...study, state: "cancelled", current: false });
  const refresh = vi.spyOn(plotloomApi, "refreshArtReferenceProposal").mockResolvedValue({ state: "awaiting_delivery", candidates: [] });
  await render({ acceptedArtCurrent: false, studies: [{ ...study, state, current: false }] });
  expect(button("准备图片生成任务")!.disabled).toBe(true);
  expect(button("取消图片任务")!.disabled).toBe(false);
  if (state === "exported") {
    expect(button("检查图像交付")!.disabled).toBe(false);
    await click("检查图像交付");
    expect(refresh).toHaveBeenCalledExactlyOnceWith("project", "study");
  }
  await click("取消图片任务");
  expect(cancel).toHaveBeenCalledExactlyOnceWith("project", "study", "Operator cancelled the F3B reference-study handoff.");
});

it.each([{ readOnly: true }, { busy: true }])("keeps stale task cleanup locked by owner or pending work: %j", async (restriction) => {
  await render({ acceptedArtCurrent: false, studies: [{ ...study, state: "exported", current: false }], ...restriction });
  expect(button("取消图片任务")!.disabled).toBe(true);
  expect(button("检查图像交付")!.disabled).toBe(true);
  expect(button("准备图片生成任务")!.disabled).toBe(true);
});
