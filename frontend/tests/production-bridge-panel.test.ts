import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { ProductionBridgeState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

const state = (label: string, revision = 1, contentHash = "a".repeat(64), text = `excerpt-${label}`): ProductionBridgeState => ({
  status: "ready", staleReasons: [], installedStageRevisions: null,
  proposal: {
    revision, contentHash, inputs: {}, scenes: [{ sceneId: `scene-${label}`, sectionId: label, episode: 1, sceneIndex: 1, cutCount: 1 }], cuts: [], conflicts: [], installable: true, preparedAt: "2026-09-22T00:00:00Z",
    intentPackage: { method: "source_excerpt_seed.v1", entries: [{ id: `entry-${label}`, targetKind: "scene_objective", targetId: `scene-${label}`, sourceCoordinates: { sectionId: label }, sourceContentHash: "b".repeat(64), method: "source_excerpt_seed.v1", suggestedText: text, text }] },
  },
});

const render = async (projectId: string) => { await act(async () => root.render(createElement(ProductionBridgePanel, { projectId, readOnly: false }))); };
const settle = async () => { await act(async () => { await Promise.resolve(); }); };
const button = (text: string) => Array.from(host.querySelectorAll("button")).find((item) => item.textContent === text) as HTMLButtonElement;
const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => { resolve = resolvePromise; reject = rejectPromise; });
  return { promise, resolve, reject };
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("requires the displayed source-excerpt package to be saved before accepting its exact new revision", async () => {
  const first = state("first");
  const saved = state("first", 2, "c".repeat(64), "author-reviewed objective");
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(first);
  const save = vi.spyOn(plotloomApi, "updateProductionBridgeIntent").mockResolvedValue(saved);
  const accept = vi.spyOn(plotloomApi, "acceptProductionBridge").mockResolvedValue({ ...saved, status: "accepted", installedStageRevisions: { story_bible: 1, scene_beats: 1, storyboard: 1 } });

  await render("first"); await settle();
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
  await act(async () => { valueSetter?.call(textarea, "author-reviewed objective"); textarea.dispatchEvent(new Event("input", { bubbles: true })); });

  expect(button("接受并安装").disabled).toBe(true);
  expect(host.textContent).toContain("当前编辑尚未保存");
  await act(async () => button("接受并安装").click());
  expect(accept).not.toHaveBeenCalled();

  await act(async () => button("保存来源摘录整包").click()); await settle();
  expect(save).toHaveBeenCalledWith("first", { expectedProposalRevision: 1, expectedContentHash: "a".repeat(64), entries: [{ id: "entry-first", text: "author-reviewed objective" }] });
  expect(button("接受并安装").disabled).toBe(false);
  await act(async () => button("接受并安装").click()); await settle();
  expect(accept).toHaveBeenCalledWith("first", { expectedProposalRevision: 2, expectedContentHash: "c".repeat(64) });
});

it("ignores a late successful GET from the prior project in the same mounted root", async () => {
  const prior = deferred<ProductionBridgeState>(); const current = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((projectId) => projectId === "prior" ? prior.promise : current.promise);

  await render("prior"); await render("current");
  await act(async () => prior.resolve(state("prior"))); await settle();
  expect(host.textContent).not.toContain("excerpt-prior");
  await act(async () => current.resolve(state("current"))); await settle();
  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("excerpt-prior");
});

it("ignores a late rejected GET and mutation from the prior project", async () => {
  const priorGet = deferred<ProductionBridgeState>(); const currentGet = deferred<ProductionBridgeState>(); const priorPrepare = deferred<ProductionBridgeState>();
  vi.spyOn(plotloomApi, "getProductionBridge").mockImplementation((projectId) => projectId === "prior" ? priorGet.promise : currentGet.promise);
  vi.spyOn(plotloomApi, "prepareProductionBridge").mockReturnValue(priorPrepare.promise);

  await render("prior");
  await act(async () => priorGet.resolve({ status: "missing", staleReasons: [], installedStageRevisions: null, proposal: null })); await settle();
  await act(async () => button("准备投产提案").click());
  await render("current");
  await act(async () => { priorGet.reject(new Error("late prior GET")); priorPrepare.resolve(state("prior")); currentGet.resolve(state("current")); }); await settle();

  expect(host.textContent).toContain("excerpt-current");
  expect(host.textContent).not.toContain("late prior GET");
  expect(host.textContent).not.toContain("excerpt-prior");
});
