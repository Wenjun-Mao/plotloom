import { act, createElement, useLayoutEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { useBranchSuggestions } from "../src/features/branches/useBranchSuggestions";
import type { BranchTaskState } from "../src/types";
import { branchOperationFixture, branchOperationView } from "./branch-operation-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const task: BranchTaskState = { candidate: null, plannedTopology: null, infeasibleReason: null, staleReasons: [] };
let root: Root;
let host: HTMLDivElement;
let owner: ReturnType<typeof branchOperationFixture>;
let observations: { version: number; pending: boolean; state: BranchTaskState | undefined; busy: boolean;
  mutate: ReturnType<typeof useBranchSuggestions>["mutate"]; adopt: ReturnType<typeof useBranchSuggestions>["adopt"] }[];
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  owner = branchOperationFixture(); observations = [];
  vi.spyOn(plotloomApi, "getBranchSuggestions").mockResolvedValue(task);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

function Probe({ projectId, basis }: { projectId: string; basis: string }) {
  const result = useBranchSuggestions(projectId, basis, false, vi.fn());
  // Observe the committed render before passive effects can clear obsolete data.
  useLayoutEffect(() => {
    const snapshot = owner.snapshot(projectId);
    observations.push({ version: snapshot.version, pending: snapshot.pending, state: result.state, busy: result.busy, mutate: result.mutate, adopt: result.adopt });
  });
  return null;
}
async function render(projectId = "A", basis = "basis1") {
  await act(async () => root.render(branchOperationView(owner, createElement(Probe, { projectId, basis }))));
}
function holdNextRead() {
  vi.mocked(plotloomApi.getBranchSuggestions).mockReturnValue(new Promise(() => undefined));
  observations = [];
}

it.each(["project", "basis"])("refuses the previous read in the first %s-change render", async change => {
  await render(); expect(observations.at(-1)?.state).toBe(task);
  holdNextRead(); await render(change === "project" ? "B" : "A", change === "basis" ? "basis2" : "basis1");
  expect(observations[0].state).toBeUndefined();
  expect(observations[0].busy).toBe(true);
});

it("refuses precommit data in the first mutation-completion render", async () => {
  await render(); holdNextRead();
  await act(async () => { await owner.run("A", async () => undefined); });
  const completed = observations.filter(item => item.version === 1 && !item.pending);
  expect(completed.length).toBeGreaterThan(0);
  for (const item of completed) { expect(item.state).toBeUndefined(); expect(item.busy).toBe(true); }
  const command = vi.fn().mockResolvedValue(task);
  expect(await completed[0].mutate(command)).toBe(false);
  expect(command).not.toHaveBeenCalled();
});

it("refuses a retained callback after its acknowledged project changes", async () => {
  await render(); const previous = observations.at(-1)!;
  holdNextRead(); await render("B");
  const command = vi.fn().mockResolvedValue(task);
  expect(await previous.mutate(command)).toBe(false);
  expect(command).not.toHaveBeenCalled();
});

it.each(["project", "basis"])("refuses a retained adoption after its acknowledged %s changes", async change => {
  vi.mocked(plotloomApi.getBranchSuggestions).mockResolvedValue({ ...task,
    candidate: { jobId: "old-job", status: "ready", suggestion: null, reportAvailable: false } });
  const draftRead = vi.spyOn(plotloomApi, "getBranchDraft");
  await render(); const previous = observations.at(-1)!;
  await render(change === "project" ? "B" : "A", change === "basis" ? "basis2" : "basis1");
  await previous.adopt();
  expect(draftRead).not.toHaveBeenCalled();
});
