import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { imageJobTargetId, useImageJobDirectionDraft, useVisualIntentDraft, type IntentDraft } from "../src/visual-intent-drafts";
import { plotloomApi } from "../src/api";
import { createProjectDraftQuiescence, type ProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const saved: IntentDraft = { identityIntent: "identity", compositionIntent: "composition", styleIntent: "saved", sourceRefs: "source" };
let root: Root;
let host: HTMLDivElement;
let editor: ReturnType<typeof useVisualIntentDraft>;
let directionEditor: ReturnType<typeof useImageJobDirectionDraft>;
function Probe({ project = "project", shot = "shot", asset = "asset", base, durable = false, quiescence }: { project?: string; shot?: string; asset?: string; base?: string; durable?: boolean; quiescence?: ProjectDraftQuiescence }) {
  editor = useVisualIntentDraft(project, shot, asset, base, saved, durable ? 1 : undefined, durable, quiescence);
  return null;
}
const render = async (props: Parameters<typeof Probe>[0] = {}) => {
  await act(async () => root.render(createElement(Probe, props)));
};
const edit = async (styleIntent: string) => {
  await act(async () => editor.update((value) => ({ ...value, styleIntent })));
};
function DirectionProbe({ project = "project", shot = "shot", target = "original", context = "approval-1", durable = false, quiescence }: { project?: string; shot?: string; target?: string; context?: string; durable?: boolean; quiescence?: ProjectDraftQuiescence }) {
  directionEditor = useImageJobDirectionDraft(project, shot, target === "original" ? { kind: "original" } : { kind: "refinement", parentCandidateAssetId: target }, context, durable ? 1 : undefined, durable, quiescence);
  return null;
}
const renderDirection = async (props: Parameters<typeof DirectionProbe>[0] = {}) => {
  await act(async () => root.render(createElement(DirectionProbe, props)));
};
beforeEach(() => {
  sessionStorage.clear(); localStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

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

it("refuses Close drain for a dirty visual intent with no persistable source reference", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  await render({ durable: true });
  await act(async () => Promise.resolve());
  await act(async () => editor.update((value) => ({ ...value, styleIntent: "changed", sourceRefs: "" })));
  await expect(editor.flush()).resolves.toBe(false);
  expect(editor.dirty).toBe(true);
});

it("keeps a known media draft in the project drain after its form switches shots", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue({ draftRevision: 1 } as never);
  const quiescence = createProjectDraftQuiescence();
  await render({ durable: true, quiescence });
  await act(async () => { await Promise.resolve(); });
  await edit("draft that must survive a shot switch");
  await render({ durable: true, quiescence, shot: "other" });

  await expect(quiescence.flush("project")).resolves.toBe(true);
  expect(save).toHaveBeenCalledWith("project", expect.objectContaining({
    editorScope: "visual_intent",
    entityId: "shot:asset",
  }));
});

it("keeps an acknowledged visual intent's own CAS receipt after its form switches shots", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft")
    .mockResolvedValueOnce({ draftRevision: 1 } as never)
    .mockResolvedValueOnce({ draftRevision: 2 } as never);
  const quiescence = createProjectDraftQuiescence();
  await render({ durable: true, quiescence });
  await act(async () => { await Promise.resolve(); });
  await edit("first acknowledged visual intent");
  await expect(editor.flush()).resolves.toBe(true);
  await edit("updated visual intent retained after switch");
  await render({ durable: true, quiescence, shot: "other" });

  await expect(quiescence.flush("project")).resolves.toBe(true);
  expect(save).toHaveBeenLastCalledWith("project", expect.objectContaining({
    entityId: "shot:asset",
    expectedDraftRevision: 1,
  }));
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

it("ignores corrupt image-direction entries without losing a valid entry", async () => {
  sessionStorage.setItem("plotloom:image-job-direction-drafts:v1", JSON.stringify({
    bad: { contextId: 123, value: {} },
    [JSON.stringify(["project", "shot", "original"])]: {
      contextId: "approval-1",
      value: "restored direction",
    },
  }));
  await renderDirection();
  expect(directionEditor.value).toBe("restored direction");
});

it("names each image direction target deterministically", () => {
  expect(imageJobTargetId({ kind: "original" })).toBe("original");
  expect(imageJobTargetId({ kind: "refinement", parentCandidateAssetId: "candidate-1" })).toBe("refinement:candidate-1");
  expect(imageJobTargetId({ kind: "keyframe_adaptation", profileId: "portrait", profileLabel: "Portrait" })).toBe("keyframe_adaptation:portrait");
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

it("does not report a cleared acknowledged image direction as drained until its CAS discard succeeds", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue({ draftRevision: 1 } as never);
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft").mockResolvedValue(1);
  await renderDirection({ durable: true });
  await act(async () => { await Promise.resolve(); });
  await act(async () => directionEditor.update("remove this durable direction"));
  await expect(directionEditor.flush()).resolves.toBe(true);

  await act(async () => directionEditor.update("   "));
  expect(directionEditor.dirty).toBe(true);
  await expect(directionEditor.flush()).resolves.toBe(true);
  expect(discard).toHaveBeenCalledWith("project", {
    editorScope: "image_direction",
    entityId: "shot:original",
    expectedDraftRevision: 1,
  });
});

it("keeps an acknowledged image direction's own CAS receipt after its form switches shots", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft")
    .mockResolvedValueOnce({ draftRevision: 1 } as never)
    .mockResolvedValueOnce({ draftRevision: 2 } as never);
  const quiescence = createProjectDraftQuiescence();
  await renderDirection({ durable: true, quiescence });
  await act(async () => { await Promise.resolve(); });
  await act(async () => directionEditor.update("first acknowledged direction"));
  await expect(directionEditor.flush()).resolves.toBe(true);
  await act(async () => directionEditor.update("updated direction retained after switch"));
  await renderDirection({ durable: true, quiescence, shot: "other" });

  await expect(quiescence.flush("project")).resolves.toBe(true);
  expect(save).toHaveBeenLastCalledWith("project", expect.objectContaining({
    entityId: "shot:original",
    expectedDraftRevision: 1,
  }));
});

it("retains a cleared image direction locally when its CAS discard conflicts", async () => {
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue({ draftRevision: 1 } as never);
  vi.spyOn(plotloomApi, "discardAuthoringDraft").mockRejectedValue(new Error("draft conflict"));
  await renderDirection({ durable: true });
  await act(async () => { await Promise.resolve(); });
  await act(async () => directionEditor.update("do not lose this on conflict"));
  await expect(directionEditor.flush()).resolves.toBe(true);

  await act(async () => directionEditor.update(""));
  let drained = true;
  await act(async () => { drained = await directionEditor.flush(); });
  expect(drained).toBe(false);
  expect(directionEditor.value).toBe("");
  expect(directionEditor.dirty).toBe(true);
  expect(directionEditor.serverConflict).toBe(true);
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
