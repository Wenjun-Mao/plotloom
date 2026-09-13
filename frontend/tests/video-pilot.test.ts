import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel, selectedSceneVideos } from "../src/video-pilot";
import { plotloomApi } from "../src/api";
import type { Shot, VideoJob } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

function job(projectId: string, shotId: string): VideoJob {
  return {
    id: `job-${projectId}`, projectId, state: "prepared", cancelRequestedAt: null,
    requestedSeconds: 5, current: true, selected: false, providerPredictionId: null,
    outputHash: null, observed: null, error: null, snapshot: { shot: { id: shotId, title: `Shot ${shotId}` } },
  };
}

function selectedJob(id: string, order: number, overrides: Partial<VideoJob> = {}): VideoJob {
  return {
    ...job("project", `shot-${order}`), id, state: "ingested", selected: true,
    snapshot: { shot: { id: `shot-${order}`, title: `Shot ${order}`, sceneId: "scene", order } },
    ...overrides,
  };
}

function props(projectId: string, shotId: string) {
  return {
    projectId, shot: { id: shotId, title: `Shot ${shotId}` } as Shot,
    approvalId: "approval", storyboardRevision: 1, selectionRevision: 1, readOnly: false,
  };
}

async function render(projectId: string, shotId: string) {
  await act(async () => root.render(createElement(VideoPilotPanel, props(projectId, shotId))));
  await act(async () => { await Promise.resolve(); });
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("does not let a deferred old-project submit refresh overwrite the new project", async () => {
  const oldSubmit = deferred<VideoJob>();
  const jobs = vi.spyOn(plotloomApi, "getVideoJobs").mockImplementation(async (projectId) => ({ jobs: [job(projectId, projectId === "old" ? "shot-old" : "shot-new")] }));
  vi.spyOn(plotloomApi, "submitVideoJob").mockReturnValue(oldSubmit.promise);
  await render("old", "shot-old");
  const submit = [...host.querySelectorAll("button")].find((item) => item.textContent === "提交一次");
  expect(submit).toBeDefined();
  await act(async () => submit?.click());
  await render("new", "shot-new");
  const oldCallsBeforeResolve = jobs.mock.calls.filter(([projectId]) => projectId === "old").length;
  await act(async () => { oldSubmit.resolve(job("old", "shot-old")); await Promise.resolve(); });
  expect(jobs.mock.calls.filter(([projectId]) => projectId === "old")).toHaveLength(oldCallsBeforeResolve);
  expect(host.textContent).toContain("Shot shot-new");
  expect(host.textContent).not.toContain("Shot shot-old");
});

it("keeps retrieval available after a known-ID cancel intent", async () => {
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [{ ...job("project", "shot"), state: "retrieve_needed", cancelRequestedAt: "2026-09-12T00:00:00Z" }] });
  await render("project", "shot");
  const retrieve = [...host.querySelectorAll("button")].find((item) => item.textContent === "获取结果");
  expect(retrieve?.disabled).toBe(false);
});

it("orders only current explicitly selected ingested candidates for one scene", () => {
  const first = selectedJob("first", 1);
  const second = selectedJob("second", 2);
  const stale = selectedJob("stale", 3, { current: false });
  const pending = selectedJob("pending", 4, { state: "submitted" });
  const unselected = selectedJob("unselected", 5, { selected: false });
  const otherScene = selectedJob("other", 1, { snapshot: { shot: { id: "other", sceneId: "other-scene", order: 1 } } });
  expect(selectedSceneVideos([second, stale, otherScene, pending, unselected, first], "scene").map((item) => item.id)).toEqual(["first", "second"]);
});
