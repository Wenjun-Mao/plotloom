import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject, demoRun } from "../src/demo";
import { fallbackProfiles } from "../src/app/workspace/useTextProviderProfiles";
import { useRunCommands } from "../src/app/workspace/useRunCommands";
import type { QuarantineItem } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const item: QuarantineItem = { id: "unit-1", stage: "story_graph", code: "failed", message: "failed", repairEligible: true };

async function harness(apiTextPipeline: boolean | null) {
  const run = { ...demoRun, status: "queued" as const, providerSnapshot: {
    ...demoRun.providerSnapshot, profileId: "frozen-profile", textAuthMode: "bearer" as const,
  } };
  const profile = fallbackProfiles().profiles[0];
  const profiles = { draft: profile, sessionKey: "active-secret", loaded: { current: false },
    refresh: vi.fn(async () => ({ profiles: [profile], activeProfileId: profile.profileId })),
    save: vi.fn(async () => profile), ensureFrozenCredential: vi.fn(async () => true) };
  const setError = vi.fn(), pollRun = vi.fn(async () => {}), openTrace = vi.fn(), saveBrief = vi.fn(async () => run.projectId);
  const input = { apiTextPipeline, profiles, pollRun, openTrace, setError, setBusy: vi.fn(), hasDraft: () => false,
    session: { project: demoProject, activePage: "brief", run, route: { run: run.id },
      capture: vi.fn(), isCurrent: () => true, acceptRun: vi.fn() } };
  let commands!: ReturnType<typeof useRunCommands>;
  function Harness() { commands = useRunCommands(input as never); return null; }
  const root = createRoot(document.createElement("div"));
  await act(async () => root.render(createElement(Harness)));
  return { commands, profiles, run, saveBrief, setError, openTrace, pollRun,
    unmount: () => act(async () => root.unmount()) };
}

it.each([false, null])("blocks every generic command before reads, credentials or mutations for capability %s", async capability => {
  const apiMethods = ["getStages", "startRun", "resumeRun", "cancelRun", "rebuild", "repairWorkUnit"] as const;
  const readsAndWrites = apiMethods.map(method => vi.spyOn(plotloomApi, method));
  const state = await harness(capability);
  try {
    await act(async () => {
      await state.commands.startRun(["story_bible"]);
      await state.commands.startProposal("project");
      await state.commands.startStoryboard("project");
      await state.commands.cancelRun(); await state.commands.resumeRun();
      await state.commands.repair(item); await state.commands.rebuild("story_graph");
      await state.commands.saveAndStartProposal(state.saveBrief);
    });
    for (const request of readsAndWrites) expect(request).not.toHaveBeenCalled();
    for (const request of [state.profiles.refresh, state.profiles.save, state.profiles.ensureFrozenCredential,
      state.saveBrief, state.openTrace, state.pollRun]) expect(request).not.toHaveBeenCalled();
    expect(state.setError).toHaveBeenCalledTimes(8);
    expect(state.setError.mock.lastCall?.[0]).toContain(capability === false ? "未启用 API" : "尚未读入");
  } finally { await state.unmount(); }
});

it("supported API resume and repair retain frozen profile ownership without saving or borrowing the active profile", async () => {
  const state = await harness(true);
  const resume = vi.spyOn(plotloomApi, "resumeRun").mockResolvedValue(state.run);
  const repair = vi.spyOn(plotloomApi, "repairWorkUnit").mockResolvedValue(state.run);
  try {
    await act(async () => { await state.commands.resumeRun(); await state.commands.repair(item); });
    expect(state.profiles.ensureFrozenCredential).toHaveBeenNthCalledWith(1, state.run);
    expect(state.profiles.ensureFrozenCredential).toHaveBeenNthCalledWith(2, state.run);
    expect(resume).toHaveBeenCalledWith(state.run.id, "frozen-profile", true);
    expect(repair).toHaveBeenCalledWith(state.run.id, item.id, "frozen-profile", expect.stringMatching(/^work-unit-repair-/), true);
    expect(state.profiles.save).not.toHaveBeenCalled(); expect(state.profiles.refresh).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});
