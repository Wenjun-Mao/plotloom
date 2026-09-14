import { useCallback, useRef } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { plotloomApi } from "../../api";
import { findProjectDrafts, type DraftScope } from "../../draft-registry";
import { providerSessionKeys } from "../../session-key";
import { hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "../../workspace-state";
import { authoringDraftKey, blankWorkspace, headsByStage, messageFrom, type PageId } from "./contracts";
import type { AuthoringDraft, MediaTask, PipelineRun, ProjectResource, RunProgress, ServerStageName, StageEnvelope, StageHead, StoryboardReview, ValidationIssue, WorkspaceProject } from "../../types";

type RouteRef = { current: { project: string; stage: PageId; run: string } };
type EpochRef = { current: number };
type ProfileCatalog = { profiles: Array<{ profileId: string; serverKeyAvailable: boolean }> };
type LoadError = { record: ReturnType<typeof findProjectDrafts>[number]; reason: "unavailable" };

export interface WorkspaceProjectLoadSession {
  beginProjectLoad(): void;
  acceptProjectLoad(payload: { project: ProjectResource; stages: StageEnvelope[]; run: PipelineRun | undefined; progress: RunProgress | undefined; review: StoryboardReview | null; media: MediaTask[]; drafts: AuthoringDraft[]; message: string }): void;
  rejectProjectLoad(projectId: string, error: unknown, staleDraft: LoadError | undefined): void;
  clearCanonicalRefresh(projectId: string): void;
}

interface ProjectLoaderInput {
  loadEpoch: EpochRef;
  route: RouteRef;
  localOwner: MutableRefObject<string>;
  durableDrafts: MutableRefObject<boolean>;
  profiles: {
    loaded: MutableRefObject<boolean>;
    catalog: MutableRefObject<ProfileCatalog>;
  };
  session: WorkspaceProjectLoadSession;
  serverDrafts: MutableRefObject<Map<string, AuthoringDraft>>;
  observeRun: (runId: string, projectId: string) => void;
  onLoaded: (projectId: string) => void;
}

const isAuthoringScope = (scope: string): scope is DraftScope => (
  scope === "brief"
  || scope === "story_bible"
  || scope === "story_graph"
  || scope === "scene_beats"
  || scope === "storyboard"
);

/**
 * Fetches one route-owned project aggregate. Its abort controller and stale
 * response check are deliberately colocated: navigation may cancel a request,
 * but only this owner decides whether a response may hydrate canonical state.
 */
export function useWorkspaceProjectLoader(input: ProjectLoaderInput) {
  const latest = useRef(input);
  latest.current = input;
  const controller = useRef<AbortController | undefined>(undefined);

  const abort = useCallback(() => {
    controller.current?.abort();
    controller.current = undefined;
  }, []);

  const loadProject = useCallback(async (projectId: string, epoch?: number) => {
    const current = latest.current;
    const requestEpoch = epoch ?? current.loadEpoch.current;
    const isCurrent = () => (
      requestEpoch === current.loadEpoch.current
      && current.route.current.project === projectId
    );

    if (!projectId) return;
    abort();
    const request = new AbortController();
    controller.current = request;
    current.session.beginProjectLoad();

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
      const selectedRun = current.route.current.run
        ? runs.runs.find((item) => item.id === current.route.current.run)
        : runs.runs[0];
      const missingSelectedRun = Boolean(current.route.current.run && !selectedRun);
      const progress = selectedRun ? await plotloomApi.getRunProgress(selectedRun.id) : undefined;
      const resumeBlocked = await blockedAutomaticResume(selectedRun, current, request.signal);

      if (!isCurrent()) return;
      current.session.acceptProjectLoad({ project, stages: stages.stages, run: selectedRun, progress, review, media: media.tasks, drafts, message: missingSelectedRun ? `运行 ${current.route.current.run} 不属于当前项目或已不存在。` : resumeBlocked });
      current.session.clearCanonicalRefresh(projectId);
      resumeActiveRun(selectedRun, project.id, resumeBlocked, isCurrent, current);
    } catch (error) {
      if (!isCurrent() || isAbortError(error)) return;
      const stale = findProjectDrafts(projectId)[0];
      current.session.rejectProjectLoad(projectId, error, stale ? { record: stale, reason: "unavailable" } : undefined);
    } finally {
      if (controller.current === request) controller.current = undefined;
    }
  }, [abort]);

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
      if (isCurrent()) input.session.rejectProjectLoad(projectId, error, undefined);
    });
}


function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
