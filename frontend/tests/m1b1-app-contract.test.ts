import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { ApiError, plotloomApi } from "../src/api";
import { defaultProviderSettings, demoProject, demoRun } from "../src/demo";
import type { ProjectCreationResponse, ProjectListItem, RunProgress, ServerStageName, StageEnvelope } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function resource(id: string, title: string, revision = 1): ProjectListItem {
  return {
    id,
    revision,
    brief: { ...demoProject.brief, title },
    lifecycleRevision: 1,
    lifecycleStatus: "active",
    archivedAt: null,
    createdAt: "2026-09-04T00:00:00Z",
    updatedAt: "2026-09-04T00:00:00Z",
    stageStatuses: { story_bible: "ready", story_graph: "ready", scene_beats: "ready", storyboard: "ready" },
    latestRun: null,
  };
}

function stageEnvelopes(payloads: Partial<Record<ServerStageName, unknown>> = {}): StageEnvelope[] {
  return (["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => ({
    head: {
      stage,
      revision: payloads[stage] == null ? 0 : 1,
      status: payloads[stage] == null ? "missing" : "ready",
      entityRevisionId: payloads[stage] == null ? null : `${stage}-r1`,
      contentHash: payloads[stage] == null ? null : `${stage}-hash`,
      schemaVersion: 2,
      inputRevisions: {},
      staleReasons: [],
      updatedAt: "2026-09-04T00:00:00Z",
    },
    payload: payloads[stage] ?? null,
  }));
}

function creationResponse(id: string, title: string): ProjectCreationResponse {
  return { ...resource(id, title), stages: stageEnvelopes() };
}

function button(label: string): HTMLButtonElement {
  const found = [...document.querySelectorAll("button")].find((candidate) => candidate.textContent?.includes(label));
  if (!found) throw new Error(`Button not found: ${label}`);
  return found as HTMLButtonElement;
}

function setInput(input: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => window.setTimeout(resolve, 0));
  });
}

function installProjectMocks(id: string, title: string, payloads: Partial<Record<ServerStageName, unknown>> = {}): void {
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(resource(id, title));
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes(payloads) });
}

describe("M1-B1 App integration contracts", () => {
  let root: Root;

  beforeEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
    window.history.replaceState(null, "", "/");
    document.body.innerHTML = '<div id="test-root"></div>';
    root = createRoot(document.getElementById("test-root")!);
    vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [] });
    vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [] });
    vi.spyOn(plotloomApi, "getStoryboardReview").mockRejectedValue(new ApiError("no storyboard review", 404));
    vi.spyOn(plotloomApi, "getProviderSettings").mockResolvedValue(defaultProviderSettings);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
  });

  it("projects a 422 DomainValidationError into the active scene-beat editor", async () => {
    const projectId = "domain-error-project";
    window.history.replaceState(null, "", `/?project=${projectId}&stage=beats`);
    installProjectMocks(projectId, "领域校验项目", {
      story_bible: demoProject.storyBible,
      story_graph: demoProject.storyGraph,
      scene_beats: demoProject.sceneBeats,
      storyboard: demoProject.storyboard,
    });
    const patch = vi.spyOn(plotloomApi, "patchStage").mockRejectedValue(new ApiError("domain validation failed", 422, {
      issues: [{ code: "DIALOGUE_OWNER", path: ["dialogueCues", "cue_b1", "speakerId"], message: "speaker must belong to the active scene" }],
    }));

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => setInput(document.querySelector(".beat-card textarea") as HTMLTextAreaElement, "本地编辑但服务器拒绝"));
    await act(async () => button("保存节拍计划").click());
    await flush();
    await flush();

    expect(patch).toHaveBeenCalledWith(projectId, "scene_beats", 1, expect.any(Object));
    expect(document.body.textContent).toContain("dialogueCues.cue_b1.speakerId");
    expect(document.body.textContent).toContain("speaker must belong to the active scene");
    expect(document.body.textContent).toContain("场景节拍未通过领域校验。");
  });

  it("retains a 409 draft through server reload and copies that exact draft into a new project", async () => {
    const projectId = "conflict-project";
    const localTitle = "本地冲突草稿";
    window.history.replaceState(null, "", `/?project=${projectId}`);
    installProjectMocks(projectId, "服务器标题");
    vi.spyOn(plotloomApi, "patchProject").mockRejectedValue(new ApiError("revision changed", 409));

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => setInput(document.querySelector(".form-card input") as HTMLInputElement, localTitle));
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain(localTitle);

    await act(async () => button("保存修改").click());
    await flush();

    expect(document.body.textContent).toContain("草稿版本已过期");
    expect(button("重新加载服务器版本")).toBeTruthy();
    expect(button("复制草稿为新项目")).toBeTruthy();
    expect(button("丢弃冲突草稿")).toBeTruthy();
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain(localTitle);

    vi.mocked(plotloomApi.getProject).mockResolvedValue(resource(projectId, "服务器并发版本", 2));
    await act(async () => button("重新加载服务器版本").click());
    await flush();
    await flush();

    expect(button("已加载服务器版本").disabled).toBe(true);
    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("服务器并发版本");
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain(localTitle);

    const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(creationResponse("conflict-copy", `${localTitle}（冲突副本）`));
    await act(async () => button("复制草稿为新项目").click());
    await flush();
    await flush();

    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({ brief: expect.objectContaining({ title: `${localTitle}（冲突副本）` }) }),
      expect.stringMatching(/^project-create-/),
    );
    expect(window.location.search).toContain("project=conflict-copy");
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain(localTitle);
  });

  it("renders lightweight work-unit attempt, token, seal, and failure progress in the inspector", async () => {
    const projectId = "progress-project";
    const run = { ...demoRun, id: "run-progress", projectId, status: "quarantined" as const };
    const progress: RunProgress = {
      runId: run.id,
      status: "quarantined",
      failureCode: "validation.canonical_rejected",
      failedStage: "scene_beats",
      stageProgress: [{ stage: "scene_beats", stagePlanId: "plan-1", stagePlanHash: "plan-hash", sealed: false, unitCount: 1, completedUnitCount: 1, quarantinedUnitCount: 1, repairEligibleUnitIds: [] }],
      workUnits: [{
        workUnitId: "scene-beats-unit-01", stage: "scene_beats", sequence: 2, maxAttempts: 3, status: "quarantined",
        latestAttempt: { attemptId: "attempt-02", attemptNumber: 2, attemptKind: "correction", sourceAttemptId: "attempt-01", status: "failed", outcomeCode: "SCENE_DURATION", outcomeUnknown: false, startedAt: "2026-09-04T00:00:00Z", finishedAt: "2026-09-04T00:00:01Z", inputTokens: 120, outputTokens: 44, durationMs: 1000 },
        sealed: true, repairEligible: false, repairReasonCode: null,
      }],
      actions: { canResume: false, canCancel: false, canRebuildStage: true, repairEligible: false },
    };
    window.history.replaceState(null, "", `/?project=${projectId}`);
    installProjectMocks(projectId, "运行投影项目");
    vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [run] });
    vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue(progress);

    await act(async () => root.render(createElement(App)));
    await flush();

    const inspector = document.querySelector('[data-testid="workspace-inspector"]');
    expect(inspector?.textContent).toContain("validation.canonical_rejected");
    expect(inspector?.textContent).toContain("scene_beats · #2");
    expect(inspector?.textContent).toContain("quarantined · seal yes");
    expect(inspector?.textContent).toContain("Attempt 2/3");
    expect(inspector?.textContent).toContain("token 120/44");
    expect(inspector?.textContent).toContain("SCENE_DURATION");
  });

  it("does not auto-resume a bearer run until its exact frozen profile has a key", async () => {
    const projectId = "frozen-key-project";
    const frozenProfileId = "locked_profile";
    const frozenRun = {
      ...demoRun,
      id: "run-awaiting-key",
      projectId,
      status: "queued" as const,
      providerSnapshot: {
        ...demoRun.providerSnapshot,
        profileId: frozenProfileId,
        textAuthMode: "bearer" as const,
      },
    };
    const profile = {
      profileId: frozenProfileId,
      displayName: "Locked profile",
      revision: 1,
      createdAt: "2026-09-04T00:00:00Z",
      updatedAt: "2026-09-04T00:00:00Z",
      serverKeyAvailable: false,
      configuration: { profileId: frozenProfileId, textAuthMode: "bearer" },
    } as never;
    const progress: RunProgress = {
      runId: frozenRun.id,
      status: "queued",
      failureCode: null,
      failedStage: null,
      stageProgress: [],
      workUnits: [],
      actions: { canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false },
    };
    window.history.replaceState(null, "", `/?project=${projectId}`);
    installProjectMocks(projectId, "冻结密钥项目");
    vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [frozenRun] });
    vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue(progress);
    vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue({
      profiles: [profile], activeProfileId: frozenProfileId, selectionRevision: 1, presets: {},
    } as never);
    const resume = vi.spyOn(plotloomApi, "resumeRun");

    await act(async () => root.render(createElement(App)));
    await flush();
    await flush();

    expect(resume).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain(`运行冻结在 Profile ${frozenProfileId}`);
    expect(document.body.textContent).toContain("为冻结 Profile 补 Key");
    expect(document.body.textContent).toContain("不会自动切换模型");
  });
});
