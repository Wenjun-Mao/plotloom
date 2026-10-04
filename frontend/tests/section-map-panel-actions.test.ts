import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SectionMapPanel } from "../src/pages/SectionMapPanel";
import { ReviewDraftContext } from "../src/features/authoring/ReviewDraftContext";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const mapping = {
  sections: [
    { sectionId: "opening", title: "开场", summary: "选择开始。", ending: false },
    { sectionId: "ending-a", title: "结局 A", summary: "路线 A。", ending: true },
    { sectionId: "ending-b", title: "结局 B", summary: "路线 B。", ending: true },
  ],
  choice: { choiceId: "turn", sectionId: "opening", prompt: "选择？", outcomes: [
    { outcomeId: "path-a", label: "前往 A", consequence: "发生 A。", endingSectionId: "ending-a" },
    { outcomeId: "path-b", label: "前往 B", consequence: "发生 B。", endingSectionId: "ending-b" },
  ] },
};
const accepted = { revision: 3, sourceRevision: 1, outlineRevision: 2, outlineContentHash: "outline", contentHash: "map-hash", mapping, acceptedAt: "2026-09-26" } as any;
const outline = { revision: 2, sourceRevision: 1, contentHash: "outline" } as any;
const admission = { status: "current", sectionMapRevision: 3, sectionMapContentHash: "map-hash", graphRevision: 4, graphContentHash: "graph-hash", staleReasons: [] } as any;

function render({ status = "current", graphReady = false, sourceDirty = false, admissionMismatch, busy = false, readOnly = false }: { status?: "current" | "stale"; graphReady?: boolean; sourceDirty?: boolean; admissionMismatch?: "hash" | "revision"; busy?: boolean; readOnly?: boolean } = {}) {
  const effectiveAdmission = admissionMismatch === "hash" ? { ...admission, sectionMapContentHash: "other-map" } : admissionMismatch === "revision" ? { ...admission, sectionMapRevision: 4 } : admission;
  return act(async () => root.render(createElement(SectionMapPanel, {
    outline, accepted, status, staleReasons: [], graphAdmission: effectiveAdmission, graphReady, sourceDirty, routes: [], readOnly, busy,
    onSave: () => undefined, onInstall: () => undefined, onContinue: () => undefined,
  })));
}
function button(label: string) { return Array.from(host.querySelectorAll("button")).find((item) => item.textContent === label)!; }

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("requires a saved clean map before applying and enables save after an edit", async () => {
  await render();
  const required = host.querySelectorAll("[aria-required='true']");
  expect(required).toHaveLength(11);
  for (const control of required) {
    expect(control.closest("label")?.querySelector(".required-mark")?.getAttribute("aria-hidden")).toBe("true");
    expect(control.hasAttribute("required")).toBe(false);
  }
  expect(button("保存修改").disabled).toBe(true);
  expect(button("应用到故事路线").disabled).toBe(false);
  const title = host.querySelector<HTMLInputElement>("input[value='开场']")!;
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(title, "新的开场");
  await act(async () => title.dispatchEvent(new Event("input", { bubbles: true })));
  expect(button("保存修改").disabled).toBe(false);
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(host.textContent).toContain("请先保存修改");
});

it("allows stale maps to be explicitly reconfirmed and only continues after the matching admitted graph loads", async () => {
  await render({ status: "stale", graphReady: true });
  expect(button("保存修改").disabled).toBe(false);
  expect(button("应用到故事路线").disabled).toBe(true);
  await render({ graphReady: true });
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(button("继续：角色设定").disabled).toBe(false);
  expect(host.textContent).toContain("故事路线已就绪");
});

it("keeps continuation unavailable for a mismatched admission, source edits, busy, or read-only state", async () => {
  await render({ graphReady: true, admissionMismatch: "hash" });
  expect(Array.from(host.querySelectorAll("button")).find((item) => item.textContent === "继续：角色设定")).toBeUndefined();
  await render({ graphReady: true, admissionMismatch: "revision" });
  expect(Array.from(host.querySelectorAll("button")).find((item) => item.textContent === "继续：角色设定")).toBeUndefined();
  await render({ graphReady: true, sourceDirty: true });
  expect(button("继续：角色设定").disabled).toBe(true);
  expect(host.textContent).toContain("请先保存故事内容");
  await render({ graphReady: true, busy: true });
  expect(button("继续：角色设定").disabled).toBe(true);
  await render({ graphReady: true, readOnly: true });
  expect(button("继续：角色设定").disabled).toBe(true);
});

it("never submits an old section-map buffer under a refreshed outline binding", async () => {
  sessionStorage.clear();
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  const draft = structuredClone(mapping); draft.sections[0]!.summary = "old-authority edit";
  store.update("project", "section_map", 1, "map:2:outline:3", JSON.stringify(draft));
  const save = vi.fn().mockResolvedValue(true);
  const show = (currentOutline: typeof outline) => act(async () => root.render(createElement(ReviewDraftContext.Provider, {
    value: { store, quiescence: q, projectId: "project", revision: 1, enabled: true },
    children: createElement(SectionMapPanel, { projectId: "project", outline: currentOutline, accepted, status: "current", staleReasons: [],
      graphAdmission: admission, graphReady: true, sourceDirty: false, routes: [], readOnly: false, busy: false,
      onSave: save, onInstall: () => undefined, onContinue: () => undefined }),
  })));
  await show(outline);
  expect(button("保存修改").disabled).toBe(false);
  await show({ ...outline, revision: 3, contentHash: "new-outline" });
  expect(host.textContent).toContain("保留草稿的版本已变化");
  expect(button("保存修改").disabled).toBe(true);
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(button("继续：角色设定").disabled).toBe(true);
  await act(async () => button("保存修改").click());
  expect(save).not.toHaveBeenCalled();
  await act(async () => button("丢弃保留草稿").click());
  expect(store.get("project", "section_map")).toBeUndefined();
  expect(host.querySelector<HTMLTextAreaElement>("textarea")!.value).toBe(mapping.sections[0]!.summary);
  sessionStorage.clear();
});
