import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { ReviewDraftContext } from "../src/features/authoring/ReviewDraftContext";
import { useKeyframeCompatibilityDraft } from "../src/features/media/keyframes/useKeyframeCompatibilityDraft";
import { useProjectUnloadProtection } from "../src/features/authoring/useProjectUnloadProtection";
import type { ManagedAsset, Shot } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
it("candidate A/B in one shot retain separate note identities and exact receipt chains", async () => {
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage), root = createRoot(document.createElement("div"));
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_project, request) => ({ projectId: "p", ...request, draftRevision: request.expectedDraftRevision + 1, updatedAt: "now" }));
  let editor!: ReturnType<typeof useKeyframeCompatibilityDraft>;
  function Probe({ assetId }: { assetId: string }) { editor = useKeyframeCompatibilityDraft({ projectId: "p", shot: { id: "shot", sceneId: "scene" } as Shot, assetId, storyboardRevision: 1, asset: { originalHash: assetId, displayHash: assetId } as ManagedAsset, mediaReadPhase: "ready" }); return null; }
  const render = (assetId: string) => act(async () => root.render(createElement(ReviewDraftContext.Provider, { value: { store, quiescence: q, projectId: "p", revision: 1, enabled: true }, children: createElement(Probe, { assetId }) })));
  try {
    await render("A"); await act(async () => editor.setCompatibility("note A")); await act(async () => { expect(await q.flush("p")).toBe(true); });
    await render("B"); await act(async () => editor.setCompatibility("note B")); await act(async () => { expect(await q.flush("p")).toBe(true); });
    await render("A"); expect(editor.compatibility).toBe("note A");
    expect(save.mock.calls.map(([, request]) => request.entityId)).toEqual(["keyframe_compatibility:shot:A", "keyframe_compatibility:shot:B"]);
    const a = store.get("p", "keyframe_compatibility", "shot:A")!;
    store.update("p", "keyframe_compatibility", 1, "foreign-basis", "must not overwrite", "shot:A");
    expect(store.get("p", "keyframe_compatibility", "shot:A")?.payload.text).toBe("note A"); expect(a.conflict).toBe(true);
  } finally { await act(async () => root.unmount()); vi.restoreAllMocks(); }
});
it("Home to project refreshes global unload ownership for an unpreserved pending File", async () => {
  const q = createProjectDraftQuiescence(), root = createRoot(document.createElement("div"));
  function Probe({ projectId }: { projectId?: string }) { useProjectUnloadProtection(projectId, q); return null; }
  try {
    await act(async () => root.render(createElement(Probe)));
    q.register("p", "pending_file", async () => false, { pending: () => true, locallyPreserved: () => false });
    await act(async () => root.render(createElement(Probe, { projectId: "p" })));
    const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true);
    await act(async () => root.render(createElement(Probe, { projectId: "other" })));
    const other = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(other); expect(other.defaultPrevented).toBe(false);
  } finally { await act(async () => root.unmount()); }
});
