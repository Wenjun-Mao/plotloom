import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { BranchSuggestionPanel } from "../src/pages/BranchSuggestionPanel";
import type { BranchTaskState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;

beforeEach(() => {
  vi.clearAllMocks();
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
});

afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.restoreAllMocks();
});

function state(status: string, reportAvailable: boolean): BranchTaskState {
  return {
    candidate: {
      jobId: "branch-candidate",
      status,
      reportAvailable,
      suggestion: {
        nodes: [{ id: "opening", title: "Opening", summary: "The story begins." }],
        choices: [], joins: [], clarifications: [],
      },
    },
    staleReasons: [], plannedTopology: null, infeasibleReason: null,
  };
}

async function render(value: BranchTaskState) {
  vi.spyOn(plotloomApi, "getBranchSuggestions").mockResolvedValue(value);
  await act(async () => root.render(createElement(BranchSuggestionPanel, {
    projectId: "project", basis: "outline:1", disabled: false, cancelDisabled: false, dirty: false,
    onAdopt: vi.fn(), onPlan: vi.fn(),
  })));
  await act(async () => new Promise(resolve => setTimeout(resolve, 0)));
}

it("offers a ready candidate's original report in an admitted empty-sandbox frame", async () => {
  const ticket = { complete: vi.fn(), cancel: vi.fn() };
  vi.spyOn(plotloomApi, "admitReportRead").mockResolvedValue(ticket);
  await render(state("ready", true));

  const disclosure = host.querySelector("details");
  expect(disclosure?.querySelector("summary")?.textContent).toContain("分支建议报告");
  expect(host.textContent).toContain("阅读不会带入、保存、确认或应用路线");
  const frame = host.querySelector("iframe");
  expect(frame?.getAttribute("src")).toBe(
    "/api/v2/projects/project/branch-suggestions/branch-candidate/report?presentation=static",
  );
  expect(frame?.hasAttribute("sandbox")).toBe(true);
  expect(frame?.getAttribute("sandbox")).toBe("");
  expect(frame?.getAttribute("referrerpolicy")).toBe("no-referrer");
});

it.each([
  ["prepared", true],
  ["ready", false],
  ["cancelled", true],
] as const)("does not expose a report for %s candidates with reportAvailable=%s", async (status, available) => {
  await render(state(status, available));
  expect(host.textContent).not.toContain("分支建议报告（静态阅读）");
  expect(host.querySelector("iframe")).toBeNull();
});
