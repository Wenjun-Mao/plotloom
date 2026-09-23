import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { useMediaWorkbenchData } from "../src/features/media/useMediaWorkbenchData";
import type { VisualWorkbench } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const visual = (revision: number): VisualWorkbench => ({
  assets: [], selectionRevision: revision, visualIntents: [], reviewedKeyframes: [],
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] }, previews: [],
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function Harness({ projectId, approvalId = "approval-1" }: { projectId: string; approvalId?: string }) {
  const read = useMediaWorkbenchData({ projectId, approvalId, approvalRevision: 1, storyboardRevision: 1, shotId: "shot-1" });
  return createElement("div", null,
    createElement("span", { "data-testid": "phase" }, read.mediaReadPhase),
    createElement("span", { "data-testid": "revision" }, read.workbench.selectionRevision),
    createElement("span", { "data-testid": "jobs" }, read.imageJobs.length),
    createElement("button", { onClick: () => void read.refresh().catch(() => undefined) }, "retry"),
  );
}

async function render(projectId: string, approvalId?: string) {
  await act(async () => root.render(createElement(Harness, { projectId, approvalId })));
}

async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
function phase() { return host.querySelector('[data-testid="phase"]')?.textContent; }
function revision() { return host.querySelector('[data-testid="revision"]')?.textContent; }
function jobs() { return host.querySelector('[data-testid="jobs"]')?.textContent; }

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getImageJobs").mockResolvedValue({ configured: false, jobs: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
});
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("shows an initial read failure, then recovers through retry in the same mounted root", async () => {
  vi.spyOn(plotloomApi, "getVisualWorkbench")
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(visual(2));
  await render("one"); await settle();
  expect(phase()).toBe("error");
  await act(async () => host.querySelector("button")!.click()); await settle();
  expect(phase()).toBe("ready");
  expect(revision()).toBe("2");
});

it("invalidates a prior successful snapshot immediately during same-context refresh and on rejection", async () => {
  const pending = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench")
    .mockResolvedValueOnce(visual(1))
    .mockImplementationOnce(() => pending.promise);
  await render("one"); await settle();
  expect(phase()).toBe("ready");
  await act(async () => host.querySelector("button")!.click());
  expect(phase()).toBe("loading");
  expect(revision()).toBe("0"); // Retained data is not projected as current.
  expect(jobs()).toBe("0");
  await act(async () => pending.reject(new Error("refresh failed"))); await settle();
  expect(phase()).toBe("error");
  expect(revision()).toBe("0");
});

it("ignores late success and rejection from an old project or approval context", async () => {
  const oldSuccess = deferred<VisualWorkbench>();
  const oldFailure = deferred<VisualWorkbench>();
  vi.spyOn(plotloomApi, "getVisualWorkbench")
    .mockImplementationOnce(() => oldSuccess.promise)
    .mockResolvedValueOnce(visual(3))
    .mockImplementationOnce(() => oldFailure.promise)
    .mockResolvedValueOnce(visual(4));
  await render("old");
  await render("new"); await settle();
  expect(phase()).toBe("ready"); expect(revision()).toBe("3");
  await act(async () => oldSuccess.resolve(visual(99))); await settle();
  expect(revision()).toBe("3");
  await render("new", "approval-2");
  await render("new", "approval-3"); await settle();
  expect(phase()).toBe("ready"); expect(revision()).toBe("4");
  await act(async () => oldFailure.reject(new Error("late failure"))); await settle();
  expect(phase()).toBe("ready"); expect(revision()).toBe("4");
});
