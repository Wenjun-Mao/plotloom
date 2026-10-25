import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import { saveWorkingDraft } from "../src/features/authoring/saveWorkingDraft";
import type { AuthoringDraft } from "../src/types";
const receipt = (request: Parameters<typeof plotloomApi.saveAuthoringDraft>[1], revision = request.expectedDraftRevision + 1): AuthoringDraft => ({ projectId: "a", editorScope: request.editorScope, entityId: request.entityId,
  baseCanonicalRevision: request.baseCanonicalRevision, draftRevision: revision, payload: request.payload, updatedAt: "2026-10-24" });
beforeEach(() => vi.useFakeTimers());
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.restoreAllMocks(); });

it("reconnect synchronizes an unmounted writer after local-only preservation without Apply", async () => {
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage);
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockRejectedValue(new TypeError("offline"));
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  const apply = vi.spyOn(plotloomApi, "patchProject");
  store.update("a", "art", 1, "art:1", '{"unfinished":');
  await expect(store.flush("a", "art")).resolves.toBe(false);
  expect(store.storageFailed()).toBe(false); expect(q.pending("a")).toBe(true);
  await expect(q.preserve("a")).resolves.toBe(true); store.leave("a");
  write.mockImplementation(async (_id, request) => receipt(request));
  await q.reconnect(); expect(q.pending("a")).toBe(false);
  expect(store.get("a", "art")?.payload.text).toBe('{"unfinished":'); expect(apply).not.toHaveBeenCalled();
});
it("blocks departure only when neither the server nor the local journal preserves input", async () => {
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, { getItem: () => null, setItem: () => { throw new DOMException("quota", "QuotaExceededError"); } });
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockRejectedValue(new TypeError("offline")); vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  store.update("a", "source", 1, "source:0", "visible input");
  await expect(q.preserve("a")).resolves.toBe(false);
  expect(store.get("a", "source")?.payload.text).toBe("visible input"); expect(store.storageFailed()).toBe(true);
});
it("lost acknowledgements reconcile only the exact next revision and never replay", async () => {
  const request = { editorScope: "brief" as const, entityId: "root", baseCanonicalRevision: 1, expectedDraftRevision: 4, payload: { title: "exact" } };
  const failure = new TypeError("response lost");
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockRejectedValue(failure);
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValueOnce([receipt(request)]).mockResolvedValueOnce([receipt({ ...request, payload: { title: "competing" } })]);
  await expect(saveWorkingDraft("a", request)).resolves.toEqual(receipt(request));
  await expect(saveWorkingDraft("a", request)).rejects.toBe(failure); expect(write).toHaveBeenCalledTimes(2);
});
it("adopting A cannot discard the newer acknowledged B draft", async () => {
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage);
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_id, request) => receipt(request));
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  store.update("a", "source", 1, "source:0", "A"); await store.flush("a", "source"); const adopted = store.get("a", "source")!;
  store.update("a", "source", 1, "source:0", "B"); await store.flush("a", "source");
  await store.clear("a", "source", "", adopted);
  expect(discard).not.toHaveBeenCalled(); expect(store.get("a", "source")?.payload.text).toBe("B"); expect(store.get("a", "source")?.expectedDraftRevision).toBe(2);
  await store.clear("a", "source", "", null); expect(discard).not.toHaveBeenCalled();
});
it("separate script sections retain independent bounded JSON and receipt chains", async () => {
  const q = createProjectDraftQuiescence(), store = createReviewDraftStore(q, localStorage);
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_id, request) => receipt(request));
  store.update("a", "script", 1, "script:1:hash:reopened", '{"sectionId":"one","text":"{"}', "one");
  store.update("a", "script", 1, "script:1:hash:reopened", '{"sectionId":"two","text":"["}', "two");
  await expect(q.flush("a")).resolves.toBe(true);
  expect(write.mock.calls.map(([, request]) => request.entityId).sort()).toEqual(["script:one", "script:two"]);
  expect(store.get("a", "script", "one")?.payload.text).toContain("one"); expect(store.get("a", "script", "two")?.payload.text).toContain("two");
});
it("a cloned session client id cannot overwrite another document's unacknowledged journal", async () => {
  const first = await import("../src/features/authoring/clientJournalStorage");
  const sameSessionId = sessionStorage.getItem("plotloom:draft-client");
  first.clientJournalStorage.setItem("test-journal", JSON.stringify({ "a:source": { payload: { text: "A" } } }));
  vi.resetModules(); sessionStorage.setItem("plotloom:draft-client", sameSessionId!);
  const second = await import("../src/features/authoring/clientJournalStorage");
  expect(second.draftClientIdentity()).not.toBe(first.draftClientIdentity());
  expect(second.clientJournalStorage.retainedEntries("test-journal")).toEqual([expect.objectContaining({ key: "a:source", value: { payload: { text: "A" } } })]);
  second.clientJournalStorage.setItem("test-journal", JSON.stringify({ "a:source": { payload: { text: "B" } } }));
  expect(first.clientJournalStorage.getItem("test-journal")).toContain('"A"'); expect(second.clientJournalStorage.getItem("test-journal")).toContain('"B"');
});

it("enumerates every competing namespace beside current and legacy data, with exact discard", async () => {
  const { clientJournalStorage: storage } = await import("../src/features/authoring/clientJournalStorage");
  const key = "competing-journal", item = (text: string) => ({ payload: { editor: "source", basis: "source:0", text }, baseRevision: 1, localRevision: 1, editing: true, expectedDraftRevision: 0 });
  storage.setItem(key, JSON.stringify({ "a:source": item("current") }));
  sessionStorage.setItem(key, JSON.stringify({ "a:source": item("legacy") }));
  localStorage.setItem(`${key}:client:other-one`, JSON.stringify({ "a:source": item("one") }));
  localStorage.setItem(`${key}:client:other-two`, JSON.stringify({ "a:source": item("two") }));
  const retained = storage.retainedEntries(key);
  expect(retained.map(entry => (entry.value.payload as { text: string }).text).sort()).toEqual(["legacy", "one", "two"]);
  storage.discardRetained(retained.find(entry => entry.namespace.endsWith("other-one"))!);
  expect(storage.retainedEntries(key)).toHaveLength(2); expect(storage.getItem(key)).toContain("current");
  const old = retained.find(entry => entry.namespace.endsWith("other-two"))!;
  localStorage.setItem(old.namespace, JSON.stringify({ "a:source": item("newer") }));
  expect(() => storage.discardRetained(old)).toThrow("已变化"); expect(localStorage.getItem(old.namespace)).toContain("newer");
});
it("a fresh document resumes an exact durable receipt without routine ownership conflict", async () => {
  const { clientJournalStorage: storage } = await import("../src/features/authoring/clientJournalStorage");
  const payload = { editor: "source" as const, targetId: "", basis: "source:0", text: "matching saved edit" };
  localStorage.setItem("plotloom:review-editor-drafts:v1:client:prior-document", JSON.stringify({ "a:source": { payload, baseRevision: 1, localRevision: 2, expectedDraftRevision: 0 } }));
  const store = createReviewDraftStore(createProjectDraftQuiescence(), storage);
  store.hydrate("a", [{ projectId: "a", editorScope: "review_buffer", entityId: "source", payload, baseCanonicalRevision: 1, draftRevision: 1, updatedAt: "now" }]);
  expect(store.get("a", "source")?.payload.text).toBe(payload.text);
  expect(store.get("a", "source")?.conflict).toBeFalsy(); expect(store.retained("a", "source")).toEqual([]);
});
it("frozen input cannot resume a foreign journal and keeps that exact entry available", async () => {
  const { clientJournalStorage: storage } = await import("../src/features/authoring/clientJournalStorage");
  localStorage.setItem("plotloom:review-editor-drafts:v1:client:prior-document", JSON.stringify({ "a:source": { payload: { editor: "source", targetId: "", basis: "source:0", text: "kept" }, baseRevision: 1, localRevision: 2, expectedDraftRevision: 0 } }));
  const q = createProjectDraftQuiescence(); q.setWriteAdmission("a", false);
  const store = createReviewDraftStore(q, storage), selected = store.retained("a", "source")[0];
  expect(() => store.resumeRetained("a", "source", "", "source:0", 1, selected)).toThrow("不允许");
  expect(store.get("a", "source")).toBeUndefined(); expect(store.retained("a", "source")).toEqual([selected]);
});

it("canonical Apply selects the exact raw Brief receipt before validating conversion on the server", async () => {
  const { canonicalDraftConsumption } = await import("../src/app/workspace/contracts");
  const raw = { title: "", targetPlaythroughSeconds: "180" }, canonical = { title: "未命名故事", targetPlaythroughSeconds: 180 };
  const draft = receipt({ editorScope: "brief", entityId: "root", baseCanonicalRevision: 1, expectedDraftRevision: 0, payload: raw });
  expect(canonicalDraftConsumption(draft, "brief", 1, canonical, raw)?.draftRevision).toBe(1);
  expect(canonicalDraftConsumption(draft, "brief", 1, canonical, { ...raw, title: "newer B" })).toBeUndefined();
});
