import { beforeEach, expect, it } from "vitest";
import { discardProjectDraftCaches } from "../src/features/authoring/projectDraftCache";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";

beforeEach(() => sessionStorage.clear());
it("erases unmounted project caches without touching neighbors or session settings", () => {
  for (const key of ["plotloom:workbench-drafts:v1", "plotloom:review-editor-drafts:v1"])
    sessionStorage.setItem(key, JSON.stringify({ "a:source": { value: "remove" }, "b:source": { value: "keep" } }));
  for (const key of ["plotloom:visual-intent-drafts:v1", "plotloom:image-job-direction-drafts:v1"])
    sessionStorage.setItem(key, JSON.stringify({ '["a","shot","asset"]': { value: "remove" }, '["b","shot","asset"]': { value: "keep" } }));
  sessionStorage.setItem("plotloom:shot-presentation:a:shot", "remove");
  sessionStorage.setItem("plotloom:shot-presentation:b:shot", "keep");
  sessionStorage.setItem("unrelated-session-settings", "unchanged");
  discardProjectDraftCaches("a");
  for (const key of ["plotloom:workbench-drafts:v1", "plotloom:review-editor-drafts:v1", "plotloom:visual-intent-drafts:v1", "plotloom:image-job-direction-drafts:v1"]) {
    expect(sessionStorage.getItem(key)).not.toContain("remove"); expect(sessionStorage.getItem(key)).toContain("keep");
  }
  expect(sessionStorage.getItem("plotloom:shot-presentation:a:shot")).toBeNull();
  expect(sessionStorage.getItem("plotloom:shot-presentation:b:shot")).toBe("keep");
  expect(sessionStorage.getItem("unrelated-session-settings")).toBe("unchanged");
});

it("erases review entries loaded on another project even when no writer was registered", () => {
  const entry = (text: string) => ({ payload: { editor: "source", basis: "source:0", text }, baseRevision: 1, localRevision: 1, editing: false, expectedDraftRevision: 0 });
  sessionStorage.setItem("plotloom:review-editor-drafts:v1", JSON.stringify({ "a:source": entry("remove"), "b:source": entry("keep") }));
  const store = createReviewDraftStore(createProjectDraftQuiescence(), sessionStorage);
  discardProjectDraftCaches("a"); store.eraseProject("a");
  store.update("b", "source", 1, "source:0", "updated neighbor");
  expect(store.get("a", "source")).toBeUndefined(); expect(sessionStorage.getItem("plotloom:review-editor-drafts:v1")).not.toContain("remove");
});
