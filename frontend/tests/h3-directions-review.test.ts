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
const buildRequest = (seed: number, idempotencyKey: string): VideoJobPrepareBody => ({
  approvalId: "approval", shotId: "shot", storyboardRevision: 1,
  expectedSelectionRevision: 1, idempotencyKey, seed,
});
const render = async (identity: string, onFreeze: (value: H3ReviewedDirections, seed: number, key: string) => Promise<void> = async () => {}) => {
  await act(async () => root.render(createElement(H3DirectionsReview, {
    projectId: "project", sourceIdentity: identity, disabled: false, buildRequest, onFreeze,
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
