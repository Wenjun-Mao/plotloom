import { expect, it } from "vitest";
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
