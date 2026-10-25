import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { useProjectInitialization } from "../src/app/workspace/useProjectInitialization";
import { creationResponse, deferred } from "./app-state-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
async function harness() {
  let epoch = 0;
  const session = { activePage: "brief" as const, capture: () => ({ epoch, projectId: "", stage: "brief" as const }),
    isCurrent: (operation: { epoch: number }) => operation.epoch === epoch,
    startLocalWorkspace: vi.fn(), acceptCreatedProject: vi.fn() };
  const clear = vi.fn(), reportError = vi.fn();
  let owner!: ReturnType<typeof useProjectInitialization>;
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useProjectInitialization({ session, clearDraftWorkflow: clear, reportError }); return null; }
  await act(async () => root.render(createElement(Probe)));
  return { get owner() { return owner; }, session, clear, reportError, supersede: () => { epoch++; }, dispose: () => act(async () => root.unmount()) };
}
it("New persists an unnamed draft before a valid Brief and coalesces a double click", async () => {
  const h = await harness(), pending = deferred<ReturnType<typeof creationResponse>>();
  const create = vi.spyOn(plotloomApi, "createProject").mockReturnValue(pending.promise);
  let first!: Promise<void>, second!: Promise<void>;
  try {
    await act(async () => { first = h.owner.startBlankProject(); second = h.owner.startBlankProject(); });
    expect(create).toHaveBeenCalledOnce(); expect(create.mock.calls[0][0]).toEqual({ brief: null });
    expect(h.owner.creating).toBe(true);
    await act(async () => { pending.resolve(creationResponse("new", "")); await first; await second; });
    expect(h.session.acceptCreatedProject).toHaveBeenCalledOnce(); expect(h.owner.creating).toBe(false);
  } finally { await h.dispose(); }
});
it("lost creation response retries the immutable intent under the same key after remount", async () => {
  const h = await harness();
  const create = vi.spyOn(plotloomApi, "createProject").mockRejectedValueOnce(new Error("response lost")).mockResolvedValue(creationResponse("reserved", ""));
  await act(async () => h.owner.startBlankProject()); const first = create.mock.calls[0];
  expect(h.reportError).toHaveBeenCalledWith(expect.stringContaining("同一身份"));
  await h.dispose();
  const next = await harness();
  try {
    await act(async () => next.owner.startBlankProject());
    expect(create.mock.calls[1]).toEqual(first); expect(next.session.acceptCreatedProject).toHaveBeenCalledOnce();
    expect(Object.keys(localStorage).some(key => key.startsWith("plotloom:create-intent:"))).toBe(false);
  } finally { await next.dispose(); }
});
it("a delayed creation acknowledgement cannot attach to a newer route", async () => {
  const h = await harness(), pending = deferred<ReturnType<typeof creationResponse>>();
  vi.spyOn(plotloomApi, "createProject").mockReturnValue(pending.promise); let flight!: Promise<void>;
  try {
    await act(async () => { flight = h.owner.startBlankProject(); }); h.supersede();
    await act(async () => { pending.resolve(creationResponse("old-intent", "")); await flight; });
    expect(h.session.acceptCreatedProject).not.toHaveBeenCalled(); expect(h.session.startLocalWorkspace).not.toHaveBeenCalled();
  } finally { await h.dispose(); }
});
it("teaching preview creates nothing; explicit editable copy copies supported canon without execution history", async () => {
  const h = await harness(), create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(creationResponse("copy", demoProject.brief.title));
  try {
    await act(async () => h.owner.openSampleProject()); expect(create).not.toHaveBeenCalled();
    expect(h.session.startLocalWorkspace.mock.calls[0][1].project.teachingPreview).toBe(true);
    await act(async () => h.owner.createTeachingCopy());
    expect(create).toHaveBeenCalledExactlyOnceWith({ brief: demoProject.brief, initialStages: expect.arrayContaining([expect.objectContaining({ stage: "storyboard" })]) }, expect.any(String));
    expect(h.session.acceptCreatedProject).toHaveBeenCalledOnce();
    expect(create.mock.calls[0][0]).not.toHaveProperty("run"); expect(create.mock.calls[0][0]).not.toHaveProperty("trace");
  } finally { await h.dispose(); }
});
