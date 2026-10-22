import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import type { ApprovalDecision, ImageJob, Shot } from "../src/types";
import { ShotPresentationReview } from "../src/features/media/keyframes/ShotPresentationReview";
import { generatedCandidateState, type ShotPresentationState } from "../src/features/media/keyframes/shot-presentation";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
const shot = { id: "draft", action: "Type on the phone screen.", composition: "A phone screen.", visualIntent: "Legible reply.", motionIntent: "Hands move.", cameraMovement: "Following shot." } as Shot;
const state: ShotPresentationState = {
  revision: 0, current: true, decision: null,
  source: { shot, predecessor: null, resolvedContext: {}, sourceHash: "a".repeat(64),
    literalOptions: [{ shotId: "draft", index: 0, text: "今晚不去了，明天见。", sourceCoordinates: { flowIndex: 3 }, sourceContentHash: "b".repeat(64) }] },
};
const quiescence = createProjectDraftQuiescence();
const onLoaded = vi.fn();
function panel() {
  return createElement(ShotPresentationReview, { projectId: "project", shotId: "draft", approval: { id: "approved" } as ApprovalDecision,
    storyboardRevision: 3, readOnly: false, onLoaded, onSaved: async () => undefined, quiescence });
}
async function textarea(label: string, value: string) {
  const target = host.querySelector<HTMLTextAreaElement>(`textarea[aria-label="${label}"]`)!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(target, value);
    target.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
beforeEach(() => {
  sessionStorage.clear(); onLoaded.mockClear();
  vi.spyOn(plotloomApi, "getShotPresentation").mockResolvedValue(structuredClone(state));
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("reviews exact source pointers and explicit complete-draft treatment before saving", async () => {
  const save = vi.spyOn(plotloomApi, "reviewShotPresentation").mockImplementation(async (_project, _shot, review) => ({
    ...state, revision: 1, decision: { id: "decision", revision: 1, sourceHash: state.source.sourceHash,
      effectiveShot: { ...shot, ...review.physical }, review },
  }));
  await act(async () => root.render(panel()));
  expect(host.querySelectorAll("textarea[aria-required='true']")).toHaveLength(4);
  expect(host.querySelector("textarea[aria-label='呈现调整 视觉意图']")?.hasAttribute("aria-required")).toBe(false);
  expect(host.querySelector("textarea[aria-label='呈现调整 动态意图']")?.hasAttribute("aria-required")).toBe(false);
  await textarea("呈现调整 实际动作", "Review the complete unsent draft.");
  await textarea("呈现调整理由", "Author approved a popped-out draft preview.");
  const select = host.querySelector<HTMLSelectElement>("select[aria-label='消息呈现']")!;
  await act(async () => { select.value = "popped_out_draft"; select.dispatchEvent(new Event("change", { bubbles: true })); });
  const button = Array.from(host.querySelectorAll<HTMLButtonElement>("button")).find(button => button.textContent === "保存此镜头的呈现审阅")!;
  expect(button.disabled).toBe(true);
  expect(save).not.toHaveBeenCalled();
  await act(async () => (host.querySelectorAll<HTMLInputElement>("input[type='checkbox']")[1]).click());
  expect(button.disabled).toBe(false);
  await act(async () => button.click());
  const review = save.mock.calls[0][2];
  expect(review.literalSources).toEqual([{ shotId: "draft", index: 0 }]);
  expect(review.messagePresentation).toBe("popped_out_draft");
  expect(review.sourceHash).toBe(state.source.sourceHash);
  expect(review.reviewed).toBe(true);
  expect(JSON.stringify(review)).not.toContain("今晚");
  expect(onLoaded).toHaveBeenLastCalledWith(1);
  expect(await quiescence.flush("project")).toBe(true);
});

it("retains the local review draft on remount and keeps Close blocked until review or discard", async () => {
  await act(async () => root.render(panel()));
  await textarea("呈现调整理由", "Unfinished author decision.");
  expect(await quiescence.flush("project")).toBe(false);
  await act(async () => root.render(null));
  expect(await quiescence.flush("project")).toBe(false);
  await act(async () => root.render(panel()));
  expect(host.querySelector<HTMLTextAreaElement>("textarea[aria-label='呈现调整理由']")?.value).toBe("Unfinished author decision.");
  const discard = Array.from(host.querySelectorAll<HTMLButtonElement>("button")).find(button => button.textContent?.includes("放弃草稿"))!;
  await act(async () => discard.click());
  expect(await quiescence.flush("project")).toBe(true);
});

it("does not permit a recovered draft to borrow a changed source hash", async () => {
  await act(async () => root.render(panel()));
  await textarea("呈现调整理由", "Retain this earlier review.");
  await act(async () => root.render(null));
  vi.mocked(plotloomApi.getShotPresentation).mockResolvedValue({ ...state, source: { ...state.source, sourceHash: "c".repeat(64) } });
  await act(async () => root.render(panel()));
  expect(host.textContent).toContain("保留的草稿基于较早来源");
  const checkbox = host.querySelectorAll<HTMLInputElement>("input[type='checkbox']")[1];
  expect(checkbox.disabled).toBe(true);
});

it("distinguishes an unbound current delivered image from stale history", () => {
  const jobs = [{ current: true, deliveries: [{ candidates: [{ assetId: "new" }] }] },
    { current: false, deliveries: [{ candidates: [{ assetId: "old" }] }] }] as unknown as ImageJob[];
  expect(generatedCandidateState("new", jobs)).toBe("current");
  expect(generatedCandidateState("old", jobs)).toBe("history");
  expect(generatedCandidateState("import", jobs)).toBe("imported");
});
