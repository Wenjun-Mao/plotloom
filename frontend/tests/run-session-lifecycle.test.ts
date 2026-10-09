import { act, createElement, StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { useRunSession } from "../src/app/workspace/useRunSession";
import type { RunProgress } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const terminal: RunProgress = {
  runId: "run-1", status: "succeeded", failureCode: null, failedStage: null,
  stageProgress: [], workUnits: [],
  actions: { canResume: false, canCancel: false, canRebuildStage: false, repairEligible: false },
};
let root: Root | undefined;
let observer: ReturnType<typeof useRunSession>;
let input: Parameters<typeof useRunSession>[0];

function deferred() {
  let resolve!: (progress: RunProgress) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<RunProgress>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function Harness() {
  observer = useRunSession(input);
  return null;
}

it("refuses native observation and trace reads even when called directly", async () => {
  input.apiTextPipeline = false;
  const progress = vi.spyOn(plotloomApi, "getRunProgress");
  const trace = vi.spyOn(plotloomApi, "getTrace");
  const execution = vi.spyOn(plotloomApi, "getRunExecutionTrace");
  await mount();
  await act(async () => {
    await observer.pollRun("retained", "project-1");
    await observer.loadTraceEvidence("retained", "project-1");
  });
  expect(progress).not.toHaveBeenCalled(); expect(trace).not.toHaveBeenCalled(); expect(execution).not.toHaveBeenCalled();
});

async function mount(strict = false) {
  root = createRoot(document.createElement("div"));
  await act(async () => root!.render(strict
    ? createElement(StrictMode, null, createElement(Harness))
    : createElement(Harness)));
}

async function unmount() {
  await act(async () => root?.unmount());
  root = undefined;
}

beforeEach(() => {
  const route = { project: "project-1", stage: "brief" as const, entity: "", run: "", hash: "" };
  input = { apiTextPipeline: true,
    session: {
      route, routeRef: { current: route },
      capture: vi.fn(() => ({ epoch: 1, projectId: route.project, stage: route.stage })),
      isCurrent: vi.fn(() => true),
      registerNavigationCleanup: vi.fn(() => () => undefined),
      clearTrace: vi.fn(), acceptRunProgress: vi.fn(),
      reloadCanonicalProject: vi.fn().mockResolvedValue(undefined),
      acceptTraceEvidence: vi.fn(),
    },
    setError: vi.fn(), describeError: (error) => String(error),
  };
});
afterEach(async () => { await unmount(); vi.restoreAllMocks(); });

it("observes terminal progress and refreshes canonical content after StrictMode setup is replayed", async () => {
  const progress = vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue(terminal);
  await mount(true);
  await act(async () => observer.pollRun("run-1", "project-1"));
  expect(progress).toHaveBeenCalledExactlyOnceWith("run-1");
  expect(input.session.acceptRunProgress).toHaveBeenCalledWith("run-1", terminal);
  expect(input.session.reloadCanonicalProject).toHaveBeenCalledExactlyOnceWith("project-1", 1);
});

it("does not accept progress or reload after the observer really unmounts", async () => {
  const held = deferred();
  const progress = vi.spyOn(plotloomApi, "getRunProgress").mockReturnValue(held.promise);
  await mount();
  let polling!: Promise<void>;
  await act(async () => { polling = observer.pollRun("run-1", "project-1"); });
  expect(progress).toHaveBeenCalledExactlyOnceWith("run-1");
  await unmount();
  await act(async () => { held.resolve(terminal); await polling; });
  expect(input.session.acceptRunProgress).not.toHaveBeenCalled();
  expect(input.session.reloadCanonicalProject).not.toHaveBeenCalled();
  expect(input.setError).not.toHaveBeenCalled();
});

it("retains route-currentness refusal when a held progress read settles after navigation", async () => {
  const held = deferred();
  const progress = vi.spyOn(plotloomApi, "getRunProgress").mockReturnValue(held.promise);
  await mount(true);
  let polling!: Promise<void>;
  await act(async () => { polling = observer.pollRun("run-1", "project-1"); });
  expect(progress).toHaveBeenCalledExactlyOnceWith("run-1");
  vi.mocked(input.session.isCurrent).mockReturnValue(false);
  await act(async () => { held.resolve(terminal); await polling; });
  expect(input.session.acceptRunProgress).not.toHaveBeenCalled();
  expect(input.session.reloadCanonicalProject).not.toHaveBeenCalled();
});

it("does not report a late progress error after unmount", async () => {
  const held = deferred();
  const progress = vi.spyOn(plotloomApi, "getRunProgress").mockReturnValue(held.promise);
  await mount();
  let polling!: Promise<void>;
  await act(async () => { polling = observer.pollRun("run-1", "project-1"); });
  expect(progress).toHaveBeenCalledExactlyOnceWith("run-1");
  await unmount();
  await act(async () => { held.reject(new Error("late failure")); await polling; });
  expect(input.setError).not.toHaveBeenCalled();
});
