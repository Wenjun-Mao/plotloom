import { expect, it, vi } from "vitest";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";

it("drains only the requested project's writers", async () => {
  const quiescence = createProjectDraftQuiescence();
  const calls: string[] = [];
  quiescence.register("first", "intent", async () => { calls.push("first"); return true; });
  quiescence.register("second", "direction", async () => { calls.push("second"); return true; });

  await expect(quiescence.flush("first")).resolves.toBe(true);
  expect(calls).toEqual(["first"]);
});

it("refuses Close when a writer fails or changes while a drain is in flight", async () => {
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("project", "failed", async () => false);
  await expect(quiescence.flush("project")).resolves.toBe(false);

  const late = createProjectDraftQuiescence();
  let release!: () => void;
  late.register("project", "intent", () => new Promise((resolve) => { release = () => resolve(true); }));
  const closing = late.flush("project");
  late.register("project", "intent", async () => true);
  release();
  await expect(closing).resolves.toBe(false);
});

it("holds project admission from drain through the Close response", async () => {
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("project", "draft", async () => true);

  const close = quiescence.beginClose("project");
  expect(quiescence.isClosing("project")).toBe(true);
  await expect(close.drain()).resolves.toBe(true);
  expect(close.canCommit()).toBe(true);

  // A mounted editor cannot add a replacement queue behind this Close.
  quiescence.register("project", "late", async () => false);
  expect(close.canCommit()).toBe(true);
  close.finish();
  expect(quiescence.isClosing("project")).toBe(false);
  expect(close.canCommit()).toBe(false);
});

it("commits a no-writer project never loaded in this tab", async () => {
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("current", "draft", async () => false);
  const close = quiescence.beginClose("other");
  await expect(close.drain()).resolves.toBe(true);
  expect(close.canCommit()).toBe(true);
  close.finish();
});

it("force discard is project-scoped and never calls save", async () => {
  const quiescence = createProjectDraftQuiescence();
  const calls: string[] = [];
  quiescence.register("first", "draft", async () => { calls.push("save"); return false; }, {
    discardUnsent: async () => { calls.push("discard-first"); }, retainOnUnmount: true,
  });
  quiescence.register("second", "draft", async () => true, { discardUnsent: async () => { calls.push("discard-second"); } });
  const close = quiescence.beginClose("first");
  await close.discardUnsent();
  expect(calls).toEqual(["discard-first"]);
  expect(quiescence.isClosing("first")).toBe(true);
  await expect(close.drain()).resolves.toBe(true);
  expect(close.canCommit()).toBe(true);
  close.finish();
});

it("suspends only the deletion target and resumes on rejection without saving or discarding", async () => {
  const q = createProjectDraftQuiescence();
  const flush = vi.fn(async () => true), discard = vi.fn(async () => undefined), resume = vi.fn();
  const other = vi.fn(async () => resume);
  q.register("a", "draft", flush, { discardUnsent: discard, suspendWrites: async () => resume });
  q.register("b", "draft", flush, { suspendWrites: other });
  const attempt = q.beginClose("a"); await attempt.suspendWrites();
  expect(flush).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled(); expect(other).not.toHaveBeenCalled();
  attempt.finish(); attempt.finish(); expect(resume).toHaveBeenCalledOnce();
});

it("resumes settled suspensions after another writer fails and never resumes erased queues", async () => {
  const q = createProjectDraftQuiescence(); const resume = vi.fn();
  q.register("a", "one", async () => true, { suspendWrites: async () => resume });
  q.register("a", "two", async () => true, { suspendWrites: async () => { throw new Error("writer failed"); } });
  const failed = q.beginClose("a"); await expect(failed.suspendWrites()).rejects.toThrow("writer failed");
  failed.finish(); expect(resume).toHaveBeenCalledOnce();
  q.register("b", "draft", async () => true, { suspendWrites: async () => resume });
  const erased = q.beginClose("b"); await erased.suspendWrites(); await erased.discardUnsent(); erased.finish();
  expect(resume).toHaveBeenCalledOnce();
});

it("withdraws only one project's retained writers and invalidates a drain across admission changes", async () => {
  const q = createProjectDraftQuiescence(); const first = vi.fn(async () => true), other = vi.fn(async () => true);
  q.register("first", "retained", first, { retainOnUnmount: true });
  q.register("other", "retained", other, { retainOnUnmount: true });
  const close = q.beginClose("first"); await expect(close.drain()).resolves.toBe(true);
  q.setWriteAdmission("first", false);
  expect(close.canCommit()).toBe(false); expect(q.canWrite("other")).toBe(true); close.finish();
  first.mockClear(); await expect(q.flush("first")).resolves.toBe(false); expect(first).not.toHaveBeenCalled();
  await expect(q.flush("other")).resolves.toBe(true); expect(other).toHaveBeenCalledOnce();
  q.setWriteAdmission("first", true); await expect(q.flush("first")).resolves.toBe(true); expect(first).toHaveBeenCalledOnce();
});
