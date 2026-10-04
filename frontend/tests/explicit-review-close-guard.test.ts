import { act, createElement, useState } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { ReviewDraftContext, useExplicitReviewCloseGuard, useReviewEditorDraft } from "../src/features/authoring/ReviewDraftContext";
import { plotloomApi } from "../src/api";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("explicit review guards stay stable during Close, block dirty input and discard only on force", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  const discard = vi.fn(); let toggle!: (dirty: boolean) => void;
  function Guard() {
    const [dirty, setDirty] = useState(false); toggle = setDirty;
    useExplicitReviewCloseGuard("project", "review", dirty, false, () => discard(), "投产审阅");
    return null;
  }
  const render = () => root.render(createElement(ReviewDraftContext.Provider, {
    value: { store, quiescence: q, projectId: "project", revision: 1, enabled: true }, children: createElement(Guard),
  }));
  try {
    await act(async () => render());
    const close = q.beginClose("project");
    await act(async () => render());
    await expect(close.drain()).resolves.toBe(true); expect(close.canCommit()).toBe(true); close.finish();
    await act(async () => toggle(true));
    const dirty = q.beginClose("project"); await expect(dirty.drain()).rejects.toThrow("投产审阅尚有未保存");
    expect(discard).not.toHaveBeenCalled(); await dirty.discardUnsent(); expect(discard).toHaveBeenCalledTimes(1); dirty.finish();
  } finally { await act(async () => root.unmount()); }
});

it("retained guards never use callbacks from a newer project in the same component", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  const discardA = vi.fn(); const discardB = vi.fn();
  function Guard({ projectId }: { projectId: string }) {
    useExplicitReviewCloseGuard(projectId, "review", true, false, projectId === "a" ? discardA : discardB, `review-${projectId}`);
    return null;
  }
  const render = (projectId: string) => root.render(createElement(ReviewDraftContext.Provider, {
    value: { store, quiescence: q, projectId, revision: 1, enabled: true }, children: createElement(Guard, { projectId }),
  }));
  try {
    await act(async () => render("a")); await act(async () => render("b"));
    const closeA = q.beginClose("a");
    await expect(closeA.drain()).rejects.toThrow("review-a尚有未保存");
    await closeA.discardUnsent(); closeA.finish();
    expect(discardA).not.toHaveBeenCalled(); expect(discardB).not.toHaveBeenCalled();
    const closeB = q.beginClose("b"); await closeB.discardUnsent(); closeB.finish();
    expect(discardB).toHaveBeenCalledTimes(1);
  } finally { await act(async () => root.unmount()); }
});

it("a late draft-discard receipt never resets a newer project's editor", async () => {
  sessionStorage.clear();
  const host = document.createElement("div"); const root = createRoot(host);
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  const discardA = vi.fn(); const discardB = vi.fn(); let release!: (revision: number) => void;
  vi.spyOn(plotloomApi, "discardAuthoringDraft").mockImplementation(() => new Promise(resolve => { release = resolve; }));
  store.hydrate("a", [{ projectId: "a", editorScope: "review_buffer", entityId: "source", baseCanonicalRevision: 1,
    draftRevision: 1, updatedAt: "2026-10-04", payload: { editor: "source", basis: "source:0", text: "{}" } }]);
  function Editor({ projectId }: { projectId: string }) {
    return useReviewEditorDraft(projectId, "source", "source:0", () => undefined, false, projectId === "a" ? discardA : discardB).notice;
  }
  const render = (projectId: string) => root.render(createElement(ReviewDraftContext.Provider, {
    value: { store, quiescence: q, projectId, revision: 1, enabled: true }, children: createElement(Editor, { projectId }),
  }));
  try {
    await act(async () => render("a"));
    const discard = Array.from(host.querySelectorAll("button")).find(button => button.textContent === "丢弃保留草稿")!;
    await act(async () => discard.click()); await act(async () => render("b"));
    await act(async () => release(1));
    expect(store.get("a", "source")).toBeUndefined();
    expect(discardA).not.toHaveBeenCalled(); expect(discardB).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); vi.restoreAllMocks(); sessionStorage.clear(); }
});
