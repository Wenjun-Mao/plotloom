import { describe, expect, it, vi } from "vitest";
import { createBranchOperationOwner } from "../src/features/branches/branchOperationOwner";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";

function deferred() {
  let resolve!: () => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<void>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

it("owns one admitted flight per project independently of subscribers", async () => {
  const owner = createBranchOperationOwner(createProjectDraftQuiescence());
  const held = deferred(); const command = vi.fn(() => held.promise);
  const observe = vi.fn(); const unsubscribe = owner.subscribe("A", observe);
  const first = owner.run("A", command);
  unsubscribe();
  expect(owner.snapshot("A").pending).toBe(true);
  expect(await owner.run("A", command)).toBe(false);
  expect(await owner.run("B", async () => undefined)).toBe(true);
  held.resolve();
  expect(await first).toBe(true);
  expect(command).toHaveBeenCalledTimes(1);
  expect(owner.snapshot("A")).toEqual({ pending: false, version: 1, error: "", unconfirmed: false });
  expect(owner.snapshot("B").version).toBe(1);
  expect(observe).toHaveBeenCalledTimes(1);
});

describe.each(["close", "snapshot", "force-close", "delete"])("%s lifecycle boundary", kind => {
  it("joins the sent POST without requiring its suspended refresh GET", async () => {
    const quiescence = createProjectDraftQuiescence(); const owner = createBranchOperationOwner(quiescence);
    const held = deferred(); const command = vi.fn(() => held.promise);
    const flight = owner.run("A", command);
    const attempt = quiescence.beginClose("A");
    let settled = false;
    const join = (kind === "force-close" ? attempt.discardUnsent() : kind === "delete" ? attempt.suspendWrites() : attempt.drain()).then(result => { settled = true; return result; });
    expect(await owner.run("A", command)).toBe(false);
    await Promise.resolve(); expect(settled).toBe(false);
    held.resolve(); await flight;
    const result = await join;
    if (kind === "close" || kind === "snapshot") { expect(result).toBe(true); expect(attempt.canCommit()).toBe(true); }
    expect(command).toHaveBeenCalledTimes(1);
    attempt.finish();
    // A force-close discards writer registrations; reopening must register a
    // new flight rather than letting it escape the next lifecycle drain.
    const next = deferred(); const reopened = owner.run("A", () => next.promise);
    const second = quiescence.beginClose("A"); let joined = false;
    const drainage = second.drain().then(value => { joined = true; return value; });
    await Promise.resolve(); expect(joined).toBe(false);
    next.resolve(); await reopened; expect(await drainage).toBe(true); second.finish();
  });
});

it("holds unknown results until a current successful read acknowledges them", async () => {
  const quiescence = createProjectDraftQuiescence(); const owner = createBranchOperationOwner(quiescence);
  const command = vi.fn().mockRejectedValue(new Error("outcome unknown"));
  expect(await owner.run("A", command)).toBe(false);
  expect(owner.snapshot("A").error).toBe("outcome unknown");
  expect(owner.snapshot("B").error).toBe("");
  expect(await owner.run("A", command)).toBe(false);
  owner.acknowledgeRead("A", 0);
  const attempt = quiescence.beginClose("A");
  await expect(attempt.drain()).rejects.toThrow("结果尚未确认");
  await expect(attempt.discardUnsent()).rejects.toThrow("结果尚未确认");
  await expect(attempt.suspendWrites()).rejects.toThrow("结果尚未确认");
  attempt.finish();
  owner.acknowledgeRead("A", 1);
  expect(owner.snapshot("A").unconfirmed).toBe(false);
  expect(owner.snapshot("A").error).toBe("outcome unknown");
  expect(await quiescence.flush("A")).toBe(true);
  expect(command).toHaveBeenCalledTimes(1);
});

it("checks project write admission synchronously before invoking a command", async () => {
  const quiescence = createProjectDraftQuiescence(); const owner = createBranchOperationOwner(quiescence);
  quiescence.setWriteAdmission("A", false);
  const command = vi.fn();
  expect(await owner.run("A", command)).toBe(false);
  expect(command).not.toHaveBeenCalled();
});

it("publishes pending only after its joinable flight exists", async () => {
  const quiescence = createProjectDraftQuiescence(); const owner = createBranchOperationOwner(quiescence);
  const held = deferred(); let joined = false; let drainage!: Promise<boolean>;
  owner.subscribe("A", () => {
    if (owner.snapshot("A").pending) drainage = quiescence.beginClose("A").drain().then(value => { joined = true; return value; });
  });
  const flight = owner.run("A", () => held.promise);
  // A synchronous subscriber may begin Close from the pending notification.
  await new Promise<void>(resolve => setTimeout(resolve, 0));
  expect(joined).toBe(false);
  held.resolve(); await flight; expect(await drainage).toBe(true);
});
