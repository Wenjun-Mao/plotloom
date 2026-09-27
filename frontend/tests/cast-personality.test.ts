import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CastPanel } from "../src/pages/CastPanel";
import { plotloomApi } from "../src/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const cast = { characters: [{ id: "C01", name: "林遥", persona: { personality: ["审慎（推断）", "愿意回应"], temperament: "温和克制", motivation: "回应消息", appearance: "外观（推断）", arc: "保留" }, voice: { timbre: "轻柔", other: "保留" }, evidence: ["source"] }], metadata: "preserve" };
const binding = { sourceRevision: 1, outlineRevision: 1, sectionIds: ["opening"] };
async function render(mode = "ready", value: Record<string, unknown> = cast, readOnly = false) {
  const accepted = { revision: 1, cast: value, binding, consumerMappings: [] };
  await act(async () => root.render(createElement(CastPanel, {
    projectId: "project", readOnly, loadError: "", state: { status: mode, staleReasons: [], candidate: mode === "ready" ? { status: "ready", jobId: "job", expectedCastRevision: 0, binding, cast: value } : undefined, acceptedCast: mode !== "ready" ? accepted : undefined } as any,
    onState: vi.fn(), onRefresh: async () => true, onInvalidate: vi.fn(), onTransitionComplete: vi.fn(),
  })));
}
function button(text: string) { return Array.from(host.querySelectorAll("button")).find((element) => element.textContent === text)!; }
async function change(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const prototype = element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value);
  await act(async () => element.dispatchEvent(new Event("input", { bubbles: true })));
}
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("edits real personality and temperament while preserving motivation and unrelated candidate fields", async () => {
  const accept = vi.spyOn(plotloomApi, "acceptCastCandidate").mockResolvedValue({} as any);
  await render();
  expect(host.querySelector("legend")?.textContent).toBe("林遥");
  expect(host.textContent).toContain("性格特点");
  expect(Array.from(host.querySelectorAll("label")).some((label) => label.textContent?.startsWith("动机"))).toBe(false);
  expect(host.querySelector("input")!.value).toBe("审慎");
  expect(host.querySelector(".cast-inference-notes")?.textContent).toContain("审慎（推断）");
  await change(host.querySelector("input")!, "内敛、审慎");
  await change(host.querySelector("textarea")!, "动作克制");
  await act(async () => button("接受这份角色设定").click());
  const expected = structuredClone(cast);
  expected.characters[0].persona.personality[0] = "内敛、审慎（推断）";
  expected.characters[0].persona.temperament = "动作克制";
  expect(accept.mock.calls[0][1].cast).toEqual(expected);
});

it("preserves array entries on add/delete and saves reopened edits without changing motivation", async () => {
  const save = vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue({} as any);
  await render("reopened");
  await act(async () => button("添加性格特点").click());
  await change(host.querySelectorAll("input")[2], "自主");
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="删除性格特点 1"]')!.click());
  await act(async () => button("保存角色修改").click());
  const result = save.mock.calls[0][1].cast as typeof cast;
  expect(result.characters[0].persona.personality).toEqual(["愿意回应", "自主"]);
  expect(result.characters[0].persona.motivation).toBe("回应消息");
});

it("does not use motivation as fallback for missing personality, and respects read-only", async () => {
  await render("ready", { characters: [{ id: "C01", persona: { motivation: "not personality" } }] }, true);
  expect(host.querySelectorAll("input")).toHaveLength(0);
  expect(host.querySelector("textarea")?.value).toBe("");
  expect(button("添加性格特点").disabled).toBe(true);
  expect(Array.from(host.querySelectorAll("textarea")).every((element) => element.disabled)).toBe(true);
});

it("shows the same personality and temperament in the accepted summary", async () => {
  await render("accepted");
  expect(host.querySelector("dl")?.textContent).toContain("审慎、愿意回应");
  expect(host.querySelector(".cast-inference-notes")?.textContent).toContain("审慎（推断）");
  expect(host.querySelector("dl")?.textContent).toContain("温和克制");
  expect(host.querySelector("dl")?.textContent).not.toContain("回应消息");
});

it("associates separate selectable labels with unique controls across characters", async () => {
  await render("ready", { characters: [...cast.characters, { ...cast.characters[0], id: "C02" }] });
  const labels = Array.from(host.querySelectorAll<HTMLLabelElement>(".cast-forms label"));
  expect(labels.length).toBe(14);
  expect(new Set(labels.map((label) => label.htmlFor)).size).toBe(labels.length);
  for (const label of labels) {
    expect(label.querySelector("input,textarea")).toBeNull();
    expect(label.control).not.toBeNull();
  }
});

it("keeps the complete original cast when accepting without edits", async () => {
  const accept = vi.spyOn(plotloomApi, "acceptCastCandidate").mockResolvedValue({} as any);
  await render();
  await act(async () => button("接受这份角色设定").click());
  expect(accept.mock.calls[0][1].cast).toEqual(cast);
});

it("preserves selected label text without suppressing ordinary label activation", async () => {
  await render();
  const label = Array.from(host.querySelectorAll("label")).find((item) => item.textContent === "气质与举止")!;
  const selection = window.getSelection()!;
  const range = document.createRange();
  range.selectNodeContents(label);
  selection.removeAllRanges();
  selection.addRange(range);
  const selectedClick = new MouseEvent("click", { bubbles: true, cancelable: true });
  await act(async () => label.dispatchEvent(selectedClick));
  expect(selectedClick.defaultPrevented).toBe(true);
  expect(selection.toString()).toBe("气质与举止");
  selection.removeAllRanges();
  const plainClick = new MouseEvent("click", { bubbles: true, cancelable: true });
  await act(async () => label.dispatchEvent(plainClick));
  expect(plainClick.defaultPrevented).toBe(false);
});

it("allows clearing an annotated value without returning the marker to the input", async () => {
  await render();
  const input = host.querySelector("input")!;
  await change(input, "");
  expect(input.value).toBe("");
  expect(host.querySelector(".cast-inference-notes")?.textContent).toContain("（推断）");
});

it("marks the minimum design and permits optional notes in candidate and reopened review", async () => {
  for (const mode of ["ready", "reopened"]) {
    await render(mode);
    expect(host.querySelector(".cast-field-requirements")?.textContent).toContain("每个角色至少填写一个性格特点，并提供外观描述");
    expect(host.querySelectorAll(".cast-forms textarea[required]")).toHaveLength(1);
    expect(Array.from(host.querySelectorAll(".cast-forms label")).find((label) => label.textContent?.includes("外观"))?.textContent).toContain("*");
  }
});

it("edits separate notes without rewriting descriptions or losing either note", async () => {
  const accept = vi.spyOn(plotloomApi, "acceptCastCandidate").mockResolvedValue({} as any);
  await render();
  const control = (text: string) => Array.from(host.querySelectorAll("label")).find((label) => label.textContent === text)!.control as HTMLTextAreaElement;
  await change(control("设定依据与补充说明"), "外观为创作补充。");
  await change(control("表演提示"), "两个选择都不演成错误。");
  await act(async () => button("接受这份角色设定").click());
  const result = accept.mock.calls[0][1].cast as any;
  expect(result.characters[0].reviewNotes).toEqual({ sourceNotes: "外观为创作补充。", performanceGuidance: "两个选择都不演成错误。" });
  expect(result.characters[0].persona).toEqual(cast.characters[0].persona);
});

it("shows structured notes in the accepted summary and preserves them through reopened saves", async () => {
  const value = { ...cast, characters: [{ ...cast.characters[0], reviewNotes: { sourceNotes: "外观是补充设定", performanceGuidance: "克制表演" } }] };
  await render("accepted", value);
  expect(host.querySelector(".accepted-cast-summary")?.textContent).toContain("外观是补充设定");
  const save = vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue({} as any);
  await render("reopened", value);
  await act(async () => button("保存角色修改").click());
  expect(save.mock.calls[0][1].cast).toEqual(value);
});

it("blocks confirmation until required design is repaired in both edit modes", async () => {
  for (const mode of ["ready", "reopened"]) {
    await render(mode, { characters: [{ id: "C01", persona: { personality: ["（推断）"], appearance: "  " } }] });
    const submit = button(mode === "ready" ? "接受这份角色设定" : "保存角色修改");
    expect(submit.disabled).toBe(true);
    expect(host.textContent).toContain("请至少填写一个性格特点。");
    expect(host.textContent).toContain("请填写角色外观");
    await change(host.querySelector("input")!, "审慎");
    expect(submit.disabled).toBe(true);
    await change(host.querySelector<HTMLTextAreaElement>("textarea[required]")!, "深蓝外套");
    expect(submit.disabled).toBe(false);
    expect(host.querySelectorAll('[role="alert"]')).toHaveLength(0);
    await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="删除性格特点 1"]')!.click());
    expect(submit.disabled).toBe(true);
  }
});
