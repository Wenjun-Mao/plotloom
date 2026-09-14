import { useCallback, useEffect, useRef } from "react";
import { plotloomApi } from "../../api";
import { findProjectDrafts } from "../../draft-registry";
import { providerSessionKeys } from "../../session-key";
import type { AuthoringDraft, PipelineRun } from "../../types";
import { messageFrom } from "./contracts";
import type { WorkspaceSession } from "./useWorkspaceSession";

type ProfileCatalog = { profiles: Array<{ profileId: string; serverKeyAvailable: boolean }> };
type ProjectLoaderSession = Pick<WorkspaceSession,
  "capture" | "isCurrent" | "routeRef" | "beginProjectLoad" | "acceptProjectLoad"
  | "clearCanonicalRefresh" | "rejectProjectLoad" | "registerNavigationCleanup" | "registerCanonicalReloader"
>;

interface ProjectLoaderInput {
  session: ProjectLoaderSession;
  durableDrafts: React.MutableRefObject<boolean>;
  profiles: {
    loaded: React.MutableRefObject<boolean>;
    catalog: React.MutableRefObject<ProfileCatalog>;
  };
  observeRun: (runId: string, projectId: string) => void;
  reportMessage: (message: string) => void;
}

/**
 * Fetches one route-owned project aggregate. Its abort controller and stale
 * response check are deliberately colocated: navigation may cancel a request,
 * but only the workspace session may accept its canonical snapshot.
 */
export function useWorkspaceProjectLoader(input: ProjectLoaderInput) {
  const latest = useRef(input);
  latest.current = input;
  const controller = useRef<AbortController | undefined>(undefined);

  const abort = useCallback(() => {
    controller.current?.abort();
    controller.current = undefined;
  }, []);
  useEffect(() => latest.current.session.registerNavigationCleanup(abort), [abort, input.session.registerNavigationCleanup]);
  useEffect(() => abort, [abort]);

  const loadProject = useCallback(async (projectId: string, expectedEpoch?: number) => {
    const current = latest.current;
    const operation = current.session.capture();
    if (!projectId || operation.projectId !== projectId || (expectedEpoch !== undefined && expectedEpoch !== operation.epoch)) return;

    abort();
    const request = new AbortController();
    controller.current = request;
    current.session.beginProjectLoad();
    const isCurrent = () => current.session.isCurrent(operation);

    try {
      const [project, stages, runs, media, drafts] = await Promise.all([
        plotloomApi.getProject(projectId, request.signal),
        plotloomApi.getStages(projectId, request.signal),
        plotloomApi.getProjectRuns(projectId, request.signal),
        plotloomApi.getProjectMediaTasks(projectId, request.signal),
        current.durableDrafts.current
          ? plotloomApi.getAuthoringDrafts(projectId, request.signal)
          : Promise.resolve([] as AuthoringDraft[]),
      ]);
      const storyboardHead = stages.stages.find((item) => item.head.stage === "storyboard")?.head;
      const review = storyboardHead?.revision
        ? await plotloomApi.getStoryboardReview(projectId, request.signal).catch(() => null)
        : null;
      const selectedRunId = current.session.routeRef.current.run;
      const selectedRun = selectedRunId ? runs.runs.find((item) => item.id === selectedRunId) : runs.runs[0];
      const missingSelectedRun = Boolean(selectedRunId && !selectedRun);
      const progress = selectedRun ? await plotloomApi.getRunProgress(selectedRun.id) : undefined;
      const resumeBlocked = await blockedAutomaticResume(selectedRun, current, request.signal);

      if (!isCurrent()) return;
      current.session.acceptProjectLoad({ project, stages: stages.stages, run: selectedRun, progress, review, media: media.tasks, drafts });
      current.session.clearCanonicalRefresh(projectId);
      current.reportMessage(missingSelectedRun ? `运行 ${selectedRunId} 不属于当前项目或已不存在。` : resumeBlocked);
      resumeActiveRun(selectedRun, project.id, resumeBlocked, isCurrent, current);
    } catch (error) {
      if (!isCurrent() || isAbortError(error)) return;
      const stale = findProjectDrafts(projectId)[0];
      current.session.rejectProjectLoad(stale ? { record: stale, reason: "unavailable" } : undefined);
      current.reportMessage(`无法加载项目 ${projectId}：${messageFrom(error)}。项目未加载；没有回退到示例。`);
    } finally {
      if (controller.current === request) controller.current = undefined;
    }
  }, [abort]);

  useEffect(
    () => latest.current.session.registerCanonicalReloader(loadProject),
    [input.session.registerCanonicalReloader, loadProject],
  );

  return { abort, loadProject };
}

async function blockedAutomaticResume(
  run: PipelineRun | undefined,
  input: ProjectLoaderInput,
  signal: AbortSignal,
): Promise<string> {
  if (!run || (run.status !== "queued" && run.status !== "running") || run.providerSnapshot.textAuthMode === "none") return "";
  const profileId = String(run.providerSnapshot.profileId || "default");
  let catalog = input.profiles.catalog.current;
  if (!input.profiles.loaded.current) {
    try {
      catalog = await plotloomApi.getTextProviderProfiles(signal);
    } catch (error) {
      return `运行冻结在 Profile ${profileId}；无法确认该 Profile 的密钥状态，因此没有自动恢复：${messageFrom(error)}`;
    }
  }
  const profile = catalog.profiles.find((item) => item.profileId === profileId);
  if (!profile) return `运行冻结在 Profile ${profileId}，但该 Profile 已不存在；不会自动切换模型。`;
  if (!profile.serverKeyAvailable && !providerSessionKeys.read(profileId)) {
    return `运行冻结在 Profile ${profileId}；请为这个 Profile 补充当前标签页 Key 后再继续。不会自动切换模型。`;
  }
  return "";
}

function resumeActiveRun(
  run: PipelineRun | undefined,
  projectId: string,
  blocked: string,
  isCurrent: () => boolean,
  input: ProjectLoaderInput,
) {
  if (!run || !["queued", "running", "cancel_requested"].includes(run.status)) return;
  if (run.status === "cancel_requested") {
    input.observeRun(run.id, projectId);
    return;
  }
  if (blocked) return;
  const profileId = String(run.providerSnapshot.profileId || "default");
  void plotloomApi.resumeRun(run.id, profileId, run.providerSnapshot.textAuthMode !== "none")
    .then(() => {
      if (isCurrent()) input.observeRun(run.id, projectId);
    })
    .catch((error) => {
      if (!isCurrent()) return;
      input.session.rejectProjectLoad(undefined);
      input.reportMessage(`无法加载项目 ${projectId}：${messageFrom(error)}。项目未加载；没有回退到示例。`);
    });
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
