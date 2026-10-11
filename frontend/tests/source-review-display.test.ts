import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { useSourceReviewDisplay } from "../src/pages/useSourceReviewDisplay";
import type { WorkspaceSourceReviewRead } from "../src/app/workspace/useWorkspaceSourceReview";
import type { SourceOutlineReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const state = (marker: string): SourceOutlineReviewState => ({ source: null, candidate: null, acceptedOutline: null, outlineStatus: "missing", acceptedSectionMap: null, sectionMapStatus: "missing", sectionMapStaleReasons: [marker], graphAdmission: null });

it("retains same-project display without restoring authority and never resurrects another project", async () => {
  const root = createRoot(document.createElement("div"));
  let display: SourceOutlineReviewState | null = null;
  function Probe({ projectId, owner }: { projectId: string; owner: Pick<WorkspaceSourceReviewRead, "status" | "value"> }) {
    display = useSourceReviewDisplay(projectId, owner); return null;
  }
  const show = (projectId: string, owner: Pick<WorkspaceSourceReviewRead, "status" | "value">) => act(async () => root.render(createElement(Probe, { projectId, owner })));
  try {
    await show("a", { status: "loading", value: null }); expect(display).toBeNull();
    const first = state("first"); await show("a", { status: "ready", value: first }); expect(display).toBe(first);
    for (const status of ["loading", "failed"] as const) {
      const owner = { status, value: null };
      await show("a", owner); expect(display).toBe(first); expect(owner.value).toBeNull();
    }
    const latest = state("latest"); await show("a", { status: "ready", value: latest }); expect(display).toBe(latest);
    await show("b", { status: "loading", value: null }); expect(display).toBeNull();
    await show("a", { status: "failed", value: null }); expect(display).toBeNull();
  } finally { await act(async () => root.unmount()); }
});
