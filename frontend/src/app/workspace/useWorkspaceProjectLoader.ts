import { useCallback, useEffect, useRef } from "react";
import { ApiError, plotloomApi } from "../../api";
import { findProjectDrafts } from "../../draft-registry";
import { providerSessionKeys } from "../../session-key";
import { frozenRunCredentialMessage } from "./frozenRunGuidance";
import type { AuthoringDraft, PipelineRun } from "../../types";
import { messageFrom, type ProjectLoadResult } from "./contracts";
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
    refresh: (signal?: AbortSignal) => Promise<ProfileCatalog>;
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
  const readOwner = useRef<AbortController | undefined>(undefined);

  const abort = useCallback(() => {
    readOwner.current?.abort();
    controller.current = undefined;
    readOwner.current = undefined;
  }, []);
  useEffect(() => latest.current.session.registerNavigationCleanup(abort), [abort, input.session.registerNavigationCleanup]);
  useEffect(() => abort, [abort]);

  const loadProject = useCallback(async (projectId: string, expectedEpoch?: number): Promise<ProjectLoadResult> => {
    const current = latest.current;
    const operation = current.session.capture();
    if (!projectId || operation.projectId !== projectId || (expectedEpoch !== undefined && expectedEpoch !== operation.epoch)) return "superseded";

    abort();
    const request = new AbortController();
    controller.current = request;
    readOwner.current = request;
    current.session.beginProjectLoad();
    // A same-route retry replaces the read without advancing the route epoch.
    // Signal-independent progress reads must not admit the replaced aggregate.
    const ownsRead = () => controller.current === request && !request.signal.aborted && current.session.isCurrent(operation);
    // Continuation callbacks outlive fetch cleanup, but not a replacement read.
    const isCurrent = () => readOwner.current === request && !request.signal.aborted && current.session.isCurrent(operation);

    let missingAuthority = false;
    try {
      const [project, stages, runs, media, drafts] = await Promise.all([
        plotloomApi.getProject(projectId, request.signal).catch(error => {
          missingAuthority = error instanceof ApiError && error.status === 404; throw error;
        }),
        plotloomApi.getStages(projectId, request.signal),
        plotloomApi.getProjectRuns(projectId, request.signal),
        plotloomApi.getProjectMediaTasks(projectId, request.signal),
        current.durableDrafts.current
          ? plotloomApi.getAuthoringDrafts(projectId, request.signal)
          : Promise.resolve([] as AuthoringDraft[]),
      ]);
      if (project.id !== projectId) throw new Error("项目响应与当前请求不一致");
      const storyboardHead = stages.stages.find((item) => item.head.stage === "storyboard")?.head;
      const review = storyboardHead?.revision
        ? await plotloomApi.getStoryboardReview(projectId, request.signal).catch(() => null)
        : null;
      const selectedRunId = current.session.routeRef.current.run;
      const selectedRun = selectedRunId ? runs.runs.find((item) => item.id === selectedRunId) : runs.runs[0];
      const missingSelectedRun = Boolean(selectedRunId && !selectedRun);
      const progress = selectedRun ? await plotloomApi.getRunProgress(selectedRun.id) : undefined;
      const resumeBlocked = await blockedAutomaticResume(selectedRun, current, request.signal);

      if (!ownsRead()) return "superseded";
      current.session.acceptProjectLoad({ project, stages: stages.stages, run: selectedRun, progress, review, media: media.tasks, drafts });
      current.session.clearCanonicalRefresh(projectId);
      current.reportMessage(missingSelectedRun ? `运行 ${selectedRunId} 不属于当前项目或已不存在。` : resumeBlocked);
      resumeActiveRun(selectedRun, project.id, resumeBlocked, isCurrent, current);
      return "loaded";
    } catch (error) {
      if (!ownsRead() || isAbortError(error)) return "superseded";
      const stale = findProjectDrafts(projectId)[0];
      current.session.rejectProjectLoad(stale ? { record: stale, reason: missingAuthority ? "missing" : "temporary" } : undefined);
      current.reportMessage(`无法加载项目 ${projectId}：${messageFrom(error)}。项目未加载；没有回退到示例。`);
      return "failed";
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
      catalog = await input.profiles.refresh(signal);
    } catch (error) {
      return frozenRunCredentialMessage(profileId, "read-failed", messageFrom(error));
    }
  }
  const profile = catalog.profiles.find((item) => item.profileId === profileId);
  if (!profile) return frozenRunCredentialMessage(profileId, "missing-profile");
  if (!profile.serverKeyAvailable && !providerSessionKeys.read(profileId)) {
    return frozenRunCredentialMessage(profileId, "missing-key");
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
  // The aggregate load can overlap an independently submitted run completing.
  // A resulting resume conflict is a terminal-run observation race, not a
  // project-load failure.
  void plotloomApi.resumeRun(run.id, profileId, run.providerSnapshot.textAuthMode !== "none")
    .then(() => { if (isCurrent()) input.observeRun(run.id, projectId); })
    .catch((error) => {
      if (!isCurrent()) return;
      if (error instanceof ApiError && error.status === 409) {
        // It became terminal during resume. Keep the canonical project and let
        // the normal observer load its final progress.
        input.observeRun(run.id, projectId);
        return;
      }
      input.session.rejectProjectLoad(undefined);
      input.reportMessage(`无法加载项目 ${projectId}：${messageFrom(error)}。项目未加载；没有回退到示例。`);
    });
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
