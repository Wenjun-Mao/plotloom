import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import type { H3PromptPreview, H3ReviewedDirections, VideoJobPrepareBody } from "../src/api";
import { H3DirectionsReview } from "../src/h3-directions-review";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const pending = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const source = (label: string): H3PromptPreview => ({
  sourceHash: label.repeat(64).slice(0, 64), compiledPrompt: null,
  sources: [{ path: "shot.action", text: `source-${label}`, label: `action-${label}` }],
});
const button = (name: string) => Array.from(host.querySelectorAll("button")).find((item) => item.textContent === name) as HTMLButtonElement;
const seedInput = () => host.querySelector('input[aria-label="H3 随机种子"]') as HTMLInputElement;
const setSeed = async (value: string) => {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  await act(async () => { setter.call(seedInput(), value); seedInput().dispatchEvent(new Event("input", { bubbles: true })); });
};
const reviewAndPreview = async () => {
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  await act(async () => { setter.call(textarea, "The keeper moves a brass fuse."); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
  await act(async () => (host.querySelector("input[type='checkbox']") as HTMLInputElement).click());
  await act(async () => button("预览完整 H3 提示词").click());
};
const buildRequest = (seed: number, idempotencyKey: string): VideoJobPrepareBody => ({
  approvalId: "approval", shotId: "shot", storyboardRevision: 1,
  expectedSelectionRevision: 1, idempotencyKey, seed,
});
const render = async (identity: string, onFreeze: (value: H3ReviewedDirections, seed: number, key: string) => Promise<void> = async () => {}) => {
  await act(async () => root.render(createElement(H3DirectionsReview, {
    projectId: "project", sourceIdentity: identity, sourceReady: true, disabled: false, buildRequest, onFreeze,
    keyframeHash: "a".repeat(64), quality: 8, requestedSeconds: 15, frameCount: 362,
  })));
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("discards late source success and rejection after shot identity changes", async () => {
  const old = pending<H3PromptPreview>();
  const newer = pending<H3PromptPreview>();
  vi.spyOn(plotloomApi, "previewH3Prompt").mockReturnValueOnce(old.promise).mockReturnValueOnce(newer.promise);
  await render("old");
  await act(async () => button("读取当前来源").click());
  await render("new");
  expect(button("读取当前来源").disabled).toBe(false);
  await act(async () => old.resolve(source("a")));
  expect(host.textContent).not.toContain("action-a");
  await act(async () => button("读取当前来源").click());
  await act(async () => newer.resolve(source("b")));
  expect(host.textContent).toContain("action-b");
  const staleRejection = pending<H3PromptPreview>();
  vi.spyOn(plotloomApi, "previewH3Prompt").mockReturnValueOnce(staleRejection.promise);
  await act(async () => button("读取当前来源").click());
  await render("third");
  await act(async () => staleRejection.reject(new Error("old failure")));
  expect(host.textContent).not.toContain("old failure");
  expect(button("读取当前来源").disabled).toBe(false);
});

it("holds a stable seed and key through source review, exact prompt preview, and freeze", async () => {
  const api = vi.spyOn(plotloomApi, "previewH3Prompt")
    .mockResolvedValueOnce(source("c"))
    .mockResolvedValueOnce({ ...source("c"), compiledPrompt: "reviewed exact prompt", compiledPromptSha256: "d".repeat(64) });
  const freeze = vi.fn(async (_value: H3ReviewedDirections, _seed: number, _key: string) => {});
  await render("shot", freeze);
  await act(async () => button("读取当前来源").click());
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
  await act(async () => { setter?.call(textarea, "The keeper moves a brass fuse."); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
  const checkbox = host.querySelector("input[type='checkbox']") as HTMLInputElement;
  await act(async () => checkbox.click());
  await act(async () => button("预览完整 H3 提示词").click());
  expect(host.textContent).toContain("reviewed exact prompt");
  await act(async () => button("冻结此说明并准备原片").click());
  const first = api.mock.calls[0][1]; const second = api.mock.calls[1][1];
  expect(first.seed).toBe(second.seed);
  expect(first.idempotencyKey).toBe(second.idempotencyKey);
  expect(freeze).toHaveBeenCalledWith({
    sourceHash: "c".repeat(64), reviewedEnglish: true,
    fields: [{ path: "shot.action", english: "The keeper moves a brass fuse." }],
    promptSha256: "d".repeat(64),
  }, first.seed, first.idempotencyKey);
});

it("reuses an exact creator seed and invalidates the reviewed package and request key on edit", async () => {
  const api = vi.spyOn(plotloomApi, "previewH3Prompt")
    .mockResolvedValueOnce(source("c"))
    .mockResolvedValueOnce({ ...source("c"), compiledPrompt: "old reviewed prompt", compiledPromptSha256: "d".repeat(64) })
    .mockResolvedValueOnce(source("e"))
    .mockResolvedValueOnce({ ...source("e"), compiledPrompt: "new reviewed prompt", compiledPromptSha256: "f".repeat(64) });
  const freeze = vi.fn(async (_value: H3ReviewedDirections, _seed: number, _key: string) => {});
  await render("shot", freeze);
  await setSeed("2325339575976657");
  await act(async () => button("读取当前来源").click());
  await reviewAndPreview();
  expect(host.textContent).toContain("种子 2325339575976657");
  await act(async () => button("冻结此说明并准备原片").click());
  expect(freeze.mock.calls[0][1]).toBe(2325339575976657);
  expect(api.mock.calls[0][1].seed).toBe(2325339575976657);
  expect(api.mock.calls[1][1].seed).toBe(2325339575976657);
  const oldKey = api.mock.calls[0][1].idempotencyKey;
  expect(freeze.mock.calls[0][2]).toBe(oldKey);

  await setSeed("42");
  expect(host.textContent).not.toContain("old reviewed prompt");
  expect(host.querySelector("textarea")).toBeNull();
  expect(button("冻结此说明并准备原片")).toBeUndefined();
  expect(freeze).toHaveBeenCalledTimes(1);
  await act(async () => button("读取当前来源").click());
  expect((host.querySelector("input[type='checkbox']") as HTMLInputElement).checked).toBe(false);
  expect(button("预览完整 H3 提示词").disabled).toBe(true);
  expect(api.mock.calls[2][1]).toMatchObject({ seed: 42 });
  expect(api.mock.calls[2][1].idempotencyKey).not.toBe(oldKey);
  await reviewAndPreview();
  await act(async () => button("冻结此说明并准备原片").click());
  expect(freeze.mock.calls[1][1]).toBe(42);
  expect(freeze.mock.calls[1][2]).toBe(api.mock.calls[2][1].idempotencyKey);
});

it.each(["", "-1", "1.5", "1e3", "9007199254740992", " 42 "])("rejects invalid or lossy seed %j before an API call", async (value) => {
  const api = vi.spyOn(plotloomApi, "previewH3Prompt");
  await render("shot");
  await setSeed(value);
  expect(seedInput().getAttribute("aria-invalid")).toBe("true");
  expect(button("读取当前来源").disabled).toBe(true);
  await act(async () => button("读取当前来源").click());
  expect(api).not.toHaveBeenCalled();
});

it.each(["0", "9007199254740991"])("preserves the valid seed boundary %s exactly", async (value) => {
  const api = vi.spyOn(plotloomApi, "previewH3Prompt").mockResolvedValue(source("a"));
  await render("shot");
  await setSeed(value);
  await act(async () => button("读取当前来源").click());
  expect(api.mock.calls[0][1].seed).toBe(Number(value));
});

it("locks seed editing during in-flight work and ignores its late completion after identity change", async () => {
  const old = pending<H3PromptPreview>();
  vi.spyOn(plotloomApi, "previewH3Prompt").mockReturnValueOnce(old.promise);
  await render("old");
  await setSeed("42");
  await act(async () => button("读取当前来源").click());
  expect(seedInput().disabled).toBe(true);
  await render("new");
  expect(seedInput().disabled).toBe(false);
  await act(async () => old.resolve(source("a")));
  expect(host.querySelector("textarea")).toBeNull();
});
