import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import type { AuthoringDraft } from "../src/types";

const receipt = (text: string, draftRevision = 1): AuthoringDraft => ({ projectId: "a", editorScope: "review_buffer", entityId: "source",
  baseCanonicalRevision: 1, draftRevision, payload: { editor: "source", basis: "source:0", text }, updatedAt: new Date().toISOString() });
beforeEach(() => sessionStorage.clear());
afterEach(() => vi.restoreAllMocks());

it("drains partial author text without canonical Save or acceptance", async () => {
  const q = createProjectDraftQuiescence();
  const store = createReviewDraftStore(q, sessionStorage);
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue(receipt("unfinished"));
  store.update("a", "source", 1, "source:0", "unfinished");
  const close = q.beginClose("a");
  await expect(close.drain()).resolves.toBe(true);
  expect(close.canCommit()).toBe(true);
  expect(save).toHaveBeenCalledWith("a", expect.objectContaining({ editorScope: "review_buffer", expectedDraftRevision: 0 }));
  close.finish();
  const restored = createReviewDraftStore(createProjectDraftQuiescence(), sessionStorage);
  restored.hydrate("a", [receipt("unfinished")]);
  expect(restored.get("a", "source")?.editing).toBe(false);
  expect(restored.get("a", "source")?.payload.text).toBe("unfinished");
});

it("preserves the original basis and CAS across refresh and newer typing", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  store.hydrate("a", [receipt("saved")]);
  store.update("a", "source", 1, "source:0", "local");
  store.hydrate("a", [receipt("other client", 2)]);
  store.update("a", "source", 2, "source:1", "still local");
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockRejectedValue(new Error("CAS conflict"));
  await expect(store.flush("a", "source")).resolves.toBe(false);
  expect(save).toHaveBeenCalledWith("a", expect.objectContaining({ expectedDraftRevision: 1, baseCanonicalRevision: 1,
    payload: expect.objectContaining({ basis: "source:0" }) }));
  await expect(store.clear("a", "source")).rejects.toThrow("another client");
  expect(store.get("a", "source")?.payload.text).toBe("still local");
});

it("force drops unsent buffers but never deletes acknowledged server drafts", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  store.hydrate("a", [receipt("acknowledged")]);
  store.update("a", "source", 1, "source:0", "unsent");
  store.update("b", "art", 1, "art:1", "other project");
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  const close = q.beginClose("a"); await close.discardUnsent(); close.finish();
  expect(store.get("a", "source")).toBeUndefined(); expect(store.get("b", "art")?.payload.text).toBe("other project");
  expect(save).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled();
  store.hydrate("a", [receipt("acknowledged")]);
  expect(store.get("a", "source")?.payload.text).toBe("acknowledged");
});

it("drains the last text when a first receipt is in flight", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  let release!: (draft: AuthoringDraft) => void;
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementationOnce(() => new Promise(resolve => { release = resolve; })).mockResolvedValue(receipt("new", 2));
  store.update("a", "source", 1, "source:0", "old");
  const saving = store.flush("a", "source");
  store.update("a", "source", 1, "source:0", "new");
  release(receipt("old"));
  await expect(saving).resolves.toBe(true);
  expect(plotloomApi.saveAuthoringDraft).toHaveBeenLastCalledWith("a", expect.objectContaining({ expectedDraftRevision: 1, payload: expect.objectContaining({ text: "new" }) }));
});

it("force stops the flush loop before an existing receipt settles", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  let release!: (draft: AuthoringDraft) => void;
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementationOnce(() => new Promise(resolve => { release = resolve; }));
  store.update("a", "source", 1, "source:0", "already sent");
  const saving = store.flush("a", "source");
  store.update("a", "source", 1, "source:0", "must remain unsent");
  const close = q.beginClose("a"); const discarded = close.discardUnsent();
  release(receipt("already sent"));
  await expect(saving).resolves.toBe(false); await discarded;
  expect(save).toHaveBeenCalledTimes(1); expect(store.get("a", "source")).toBeUndefined();
  close.finish();
});

it("leaving a project requires explicit recovery on reopen", () => {
  const store = createReviewDraftStore(createProjectDraftQuiescence(), sessionStorage);
  store.update("a", "source", 1, "source:0", "unfinished");
  expect(store.get("a", "source")?.editing).toBe(true);
  store.leave("a"); store.hydrate("a", [receipt("unfinished")]);
  expect(store.get("a", "source")?.editing).toBe(false);
  store.restore("a", "source"); expect(store.get("a", "source")?.editing).toBe(true);
});

it("deletion suspension joins an existing receipt but preserves newer typing until admission", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  let release!: (draft: AuthoringDraft) => void;
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementationOnce(() => new Promise(resolve => { release = resolve; })).mockResolvedValue(receipt("new", 2));
  store.update("a", "source", 1, "source:0", "old"); const saving = store.flush("a", "source");
  store.update("a", "source", 1, "source:0", "new");
  const deletion = q.beginClose("a"); const suspended = deletion.suspendWrites();
  release(receipt("old")); await suspended; await expect(saving).resolves.toBe(false);
  expect(save).toHaveBeenCalledOnce(); expect(store.get("a", "source")?.payload.text).toBe("new");
  deletion.finish(); await expect(store.flush("a", "source")).resolves.toBe(true);
  expect(save).toHaveBeenCalledTimes(2);
});

it("an archived retained review cannot save or discard after rejected deletion", async () => {
  const q = createProjectDraftQuiescence(); const store = createReviewDraftStore(q, sessionStorage);
  store.hydrate("a", [receipt("saved")]); store.update("a", "source", 1, "source:0", "local archived text");
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue(receipt("local archived text", 2));
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  q.setWriteAdmission("a", false);
  const attempt = q.beginClose("a"); await attempt.suspendWrites(); attempt.finish();
  await expect(store.flush("a", "source")).resolves.toBe(false);
  await expect(store.clear("a", "source")).rejects.toThrow("当前项目不允许修改审阅草稿");
  expect(save).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled();
  expect(store.get("a", "source")?.payload.text).toBe("local archived text");
  q.setWriteAdmission("a", true); await expect(store.flush("a", "source")).resolves.toBe(true);
  expect(save).toHaveBeenCalledOnce(); expect(save).toHaveBeenCalledWith("a", expect.objectContaining({ expectedDraftRevision: 1 }));
});
