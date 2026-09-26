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
  expect(host.textContent).toContain("性格与气质");
  expect(Array.from(host.querySelectorAll("label")).some((label) => label.textContent?.startsWith("动机"))).toBe(false);
  await change(host.querySelector("input")!, "内敛、审慎（推断）");
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
  await act(async () => button("保存重新打开的角色").click());
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
  expect(host.querySelector("dl")?.textContent).toContain("审慎（推断）、愿意回应");
  expect(host.querySelector("dl")?.textContent).toContain("温和克制");
  expect(host.querySelector("dl")?.textContent).not.toContain("回应消息");
});
