import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { StoryboardPage } from "../src/pages/StoryboardPage";
import type { StoryboardReview } from "../src/types";

vi.mock("../src/features/media/ManagedMediaWorkbench", () => ({ ManagedMediaWorkbench: () => null }));
vi.mock("../src/features/video-batch/VideoBatchPanel", () => ({ VideoBatchPanel: () => null }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const review = (approved = false, named = false) => ({
  head: { revision: 1, contentHash: "a".repeat(64), status: "ready" },
  gateEvaluation: { gateSetVersion: "storyboard.v2", results: [{ id: "gate", gateId: "coverage", entityPath: [], reason: "Coverage passes", required: true, status: "pass" }] },
  decisions: [], activeApproval: approved ? { id: "approval", subjectRevision: 1, reviewer: named ? "Retained reviewer" : "",
    ...(named ? {} : { attribution: { kind: "unnamed_creator" } }), createdAt: "2026-10-19" } : null,
}) as unknown as StoryboardReview;
const changed = vi.fn();
async function render(value = review(), overrides: Record<string, unknown> = {}) {
  await act(async () => root.render(createElement(StoryboardPage, {
    bible: demoProject.storyBible, graph: demoProject.storyGraph, sceneBeats: demoProject.sceneBeats,
    value: demoProject.storyboard, projectId: "project", revision: 1, contentHash: "a".repeat(64),
    stale: false, mediaTasks: {}, saving: false, readOnly: false, onSave: async () => undefined,
    review: value, onReviewChange: changed, ...overrides,
  })));
}
const button = () => host.querySelector<HTMLButtonElement>(".approval-actions button")!;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); changed.mockReset(); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("confirms the exact board once per click without name, note or automatic action, then explicitly revokes", async () => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  const post = vi.spyOn(plotloomApi, "decideStoryboardApproval").mockImplementation(async () => { await pending; return {} as never; });
  vi.spyOn(plotloomApi, "getStoryboardReview").mockResolvedValue(review(true));
  await render();
  expect(post).not.toHaveBeenCalled();
  expect(host.querySelector(".approval-actions input, .approval-actions textarea, details.approval-actions")).toBeNull();
  await act(async () => { button().click(); button().click(); });
  expect(post).toHaveBeenCalledTimes(1);
  expect(post).toHaveBeenCalledWith("project", { expectedRevision: 1, contentHash: "a".repeat(64),
    decision: "approve", attribution: { kind: "unnamed_creator" }, gateSetVersion: "storyboard.v2" });
  expect(button().disabled).toBe(true);
  expect(button().textContent).toBe("正在确认…");
  await act(async () => { release(); await pending; });
  expect(changed).toHaveBeenCalledWith(review(true));
  await render(review(true));
  expect(host.textContent).toContain("当前批准：创作者确认（未署名）");
  expect(button().textContent).toBe("撤销批准");
  await act(async () => button().click());
  expect(post.mock.calls[1][1]).toMatchObject({ decision: "revoke", attribution: { kind: "unnamed_creator" } });
});

it.each([{ stale: true }, { saving: true }, { readOnly: true }, { contentHash: undefined }])("locks unavailable approval %o", async overrides => {
  const post = vi.spyOn(plotloomApi, "decideStoryboardApproval");
  await render(review(), overrides);
  expect(button().disabled || button().closest("fieldset")?.disabled).toBe(true);
  await act(async () => button().click());
  expect(post).not.toHaveBeenCalled();
});

it("blocks failed gates and keeps named history truthful", async () => {
  const failed = review(); failed.gateEvaluation!.results[0].status = "fail";
  await render(failed); expect(button().disabled).toBe(true);
  await render(review(true, true));
  expect(host.textContent).toContain("当前批准：Retained reviewer");
  expect(host.textContent).not.toContain("当前批准：创作者确认");
});

it("shows submission errors and unlocks the explicit action for retry", async () => {
  vi.spyOn(plotloomApi, "decideStoryboardApproval").mockRejectedValue(new Error("exact revision changed"));
  await render();
  await act(async () => button().click());
  expect(host.querySelector('[role="alert"]')?.textContent).toContain("exact revision changed");
  expect(button().disabled).toBe(false);
});

it("discards a delayed approval response after keyed project navigation unmounts its page", async () => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  vi.spyOn(plotloomApi, "decideStoryboardApproval").mockImplementation(async () => { await pending; return {} as never; });
  vi.spyOn(plotloomApi, "getStoryboardReview").mockResolvedValue(review(true));
  await render(review(), { key: "project-A" });
  await act(async () => button().click());
  await render(review(), { key: "project-B", projectId: "project-B" });
  await act(async () => { release(); await pending; });
  expect(changed).not.toHaveBeenCalled();
  expect(button().textContent).toBe("批准当前分镜");
  expect(button().disabled).toBe(false);
});
