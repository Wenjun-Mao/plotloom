import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it } from "vitest";
import { useImageJobDirectionDraft, useVisualIntentDraft, type IntentDraft } from "../src/visual-intent-drafts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const saved: IntentDraft = { identityIntent: "identity", compositionIntent: "composition", styleIntent: "saved", sourceRefs: "source" };
let root: Root;
let host: HTMLDivElement;
let editor: ReturnType<typeof useVisualIntentDraft>;
let directionEditor: ReturnType<typeof useImageJobDirectionDraft>;
function Probe({ project = "project", shot = "shot", asset = "asset", base }: { project?: string; shot?: string; asset?: string; base?: string }) {
  editor = useVisualIntentDraft(project, shot, asset, base, saved);
  return null;
}
const render = async (props: Parameters<typeof Probe>[0] = {}) => {
  await act(async () => root.render(createElement(Probe, props)));
};
const edit = async (styleIntent: string) => {
  await act(async () => editor.update((value) => ({ ...value, styleIntent })));
};
function DirectionProbe({ project = "project", shot = "shot", target = "original", context = "approval-1" }: { project?: string; shot?: string; target?: string; context?: string }) {
  directionEditor = useImageJobDirectionDraft(project, shot, target === "original" ? { kind: "original" } : { kind: "refinement", parentCandidateAssetId: target }, context);
  return null;
}
const renderDirection = async (props: Parameters<typeof DirectionProbe>[0] = {}) => {
  await act(async () => root.render(createElement(DirectionProbe, props)));
};
beforeEach(() => {
  sessionStorage.clear(); localStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("retains separate drafts across shots, candidates, projects, and remounts in session storage only", async () => {
  await render(); await edit("my draft");
  for (const props of [{ shot: "other" }, { asset: "other" }, { project: "other" }]) {
    await render(props); expect(editor.value.styleIntent).toBe("saved"); expect(editor.dirty).toBe(false);
  }
  await render(); expect(editor.value.styleIntent).toBe("my draft"); expect(editor.dirty).toBe(true);
  await act(async () => root.unmount()); root = createRoot(host); await render();
  expect(editor.value.styleIntent).toBe("my draft");
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.getItem("plotloom:visual-intent-drafts:v1")).toContain("my draft");
});

it("preserves the original null baseline when a saved intent arrives, until explicit discard", async () => {
  await render(); await edit("local");
  await render({ base: "new-intent" }); expect(editor.stale).toBe(true);
  await edit("still local"); expect(editor.stale).toBe(true);
  await act(async () => editor.clear());
  expect(editor.stale).toBe(false); expect(editor.dirty).toBe(false); expect(editor.value).toEqual(saved);
});

it("does not silently rebase an edited existing intent", async () => {
  await render({ base: "v1" }); await edit("local"); await render({ base: "v2" });
  expect(editor.stale).toBe(true); expect(editor.value.styleIntent).toBe("local");
});

it("discards only the current context and warns on unload while any drafts remain", async () => {
  await render(); await edit("first"); await render({ shot: "second" }); await edit("second");
  await act(async () => editor.clear()); expect(editor.dirty).toBe(false);
  const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(true);
  await render(); expect(editor.value.styleIntent).toBe("first");
  await act(async () => editor.clear());
  const clean = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(clean);
  expect(clean.defaultPrevented).toBe(false);
});

it("ignores corrupt stored entries without losing valid entries", async () => {
  sessionStorage.setItem("plotloom:visual-intent-drafts:v1", JSON.stringify({
    bad: { baseId: 123, value: {} },
    [JSON.stringify(["project", "shot", "asset"])]: { baseId: null, value: { ...saved, styleIntent: "restored" } },
  }));
  await render(); expect(editor.value.styleIntent).toBe("restored");
});

it("isolates manual image directions by project, shot, and original/refinement target across remounts", async () => {
  await renderDirection();
  await act(async () => directionEditor.update("original direction"));
  await renderDirection({ shot: "other" });
  expect(directionEditor.value).toBe("");
  await act(async () => directionEditor.update("other-shot direction"));
  await renderDirection({ target: "candidate-1" });
  expect(directionEditor.value).toBe("");
  await act(async () => directionEditor.update("refinement direction"));
  await act(async () => root.unmount()); root = createRoot(host);
  await renderDirection({ target: "candidate-1" });
  expect(directionEditor.value).toBe("refinement direction");
  await renderDirection();
  expect(directionEditor.value).toBe("original direction");
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.getItem("plotloom:image-job-direction-drafts:v1")).toContain("refinement direction");
});

it("requires explicit recovery when an image direction's approval context changes", async () => {
  await renderDirection();
  await act(async () => directionEditor.update("keep the practical light"));
  await renderDirection({ context: "approval-2" });
  expect(directionEditor.value).toBe("keep the practical light");
  expect(directionEditor.stale).toBe(true);
  await act(async () => directionEditor.recoverForCurrentContext());
  expect(directionEditor.stale).toBe(false);
  await act(async () => directionEditor.clear());
  expect(directionEditor.value).toBe("");
});

it("removes empty directions without warning and preserves other exact targets", async () => {
  await renderDirection();
  await act(async () => directionEditor.update("original direction"));
  await renderDirection({ target: "candidate-1" });
  await act(async () => directionEditor.update("refinement direction"));
  await act(async () => directionEditor.update("   "));

  expect(directionEditor.value).toBe("");
  expect(directionEditor.dirty).toBe(false);
  const whileOriginalRemains = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(whileOriginalRemains);
  expect(whileOriginalRemains.defaultPrevented).toBe(true);

  await renderDirection();
  expect(directionEditor.value).toBe("original direction");
  await act(async () => directionEditor.clear());
  const clean = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(clean);
  expect(clean.defaultPrevented).toBe(false);
  expect(sessionStorage.getItem("plotloom:image-job-direction-drafts:v1")).toBe("{}");
});
