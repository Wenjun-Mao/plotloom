import { useCallback, useEffect } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { discardDraft, findProjectDrafts, hasDraft, type DraftRecord, type DraftScope } from "../../draft-registry";
import { blankWorkspace, newClientDraftOwner, routeFromLocation, stageForPage, type NavigationTarget, type PageId } from "./contracts";
import type { MediaTask, PipelineRun, RunProgress, ServerStageName, StageHead, StoryboardReview, TraceEvent, ValidationIssue, WorkspaceProject } from "../../types";

type Route = ReturnType<typeof routeFromLocation>;
type UnsafeDraft = { record: DraftRecord; reason: "archived" | "unavailable" };

export interface WorkspaceNavigationState {
  route: MutableRefObject<Route>;
  activePage: PageId;
  setActivePage: Dispatch<SetStateAction<PageId>>;
  routeEntity: string;
  setRouteEntity: Dispatch<SetStateAction<string>>;
  pending: NavigationTarget | undefined;
  setPending: Dispatch<SetStateAction<NavigationTarget | undefined>>;
}

interface WorkspaceNavigationInput {
  state: WorkspaceNavigationState;
  workspace: {
    project: WorkspaceProject;
    run: PipelineRun | undefined;
    localOwner: MutableRefObject<string>;
    setProject: Dispatch<SetStateAction<WorkspaceProject>>;
    setStageHeads: Dispatch<SetStateAction<Partial<Record<ServerStageName, StageHead>>>>;
    setRun: Dispatch<SetStateAction<PipelineRun | undefined>>;
    setProgress: Dispatch<SetStateAction<RunProgress | undefined>>;
    setReview: Dispatch<SetStateAction<StoryboardReview | null>>;
    setIssues: Dispatch<SetStateAction<Partial<Record<ServerStageName, ValidationIssue[]>>>>;
    setTrace: Dispatch<SetStateAction<TraceEvent[]>>;
    setMediaTasks: Dispatch<SetStateAction<Record<string, MediaTask>>>;
    setConnection: (value: "loading" | "connected" | "demo" | "blank" | "error") => void;
    setOnboarding: (value: boolean) => void;
  };
  drafts: {
    current: MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
    durableEnabled: MutableRefObject<boolean>;
    flush: (scope: DraftScope) => Promise<boolean>;
    commitProject: (patch: Partial<WorkspaceProject>) => Promise<void>;
    commitStage: <T>(stage: ServerStageName, content: T) => Promise<void>;
    clearRecovery: () => void;
    clearConflict: () => void;
    unsafe: UnsafeDraft | undefined;
    setUnsafe: Dispatch<SetStateAction<UnsafeDraft | undefined>>;
  };
  loader: {
    invalidate: (next: Route) => number;
    loadProject: (projectId: string, epoch?: number) => Promise<void>;
    canonicalRefreshRequired: MutableRefObject<Set<string>>;
  };
}

/**
 * Owns URL writes, history restoration, and draft-gated workspace changes.
 * Persistence supplies only the two explicit save commands; it never decides
 * which URL or project is visible after a navigation attempt.
 */
export function useWorkspaceNavigation(input: WorkspaceNavigationInput) {
  const { state, workspace, drafts, loader } = input;
  const applyNavigation = useCallback((next: NavigationTarget) => {
    const route: Route = { project: next.project, stage: next.stage, entity: next.entity, run: next.run };
    const epoch = loader.invalidate(route);
    if (next.history === "push") writeRoute(route, "push");
    drafts.current.current = undefined;
    state.setActivePage(next.stage);
    state.setRouteEntity(next.entity);
    drafts.clearRecovery();
    drafts.clearConflict();
    drafts.setUnsafe(undefined);
    if (!next.project && next.project !== (workspace.project.id || "")) {
      workspace.localOwner.current = newClientDraftOwner();
      workspace.setProject(blankWorkspace(workspace.localOwner.current));
      workspace.setStageHeads({});
      workspace.setRun(undefined);
      workspace.setProgress(undefined);
      workspace.setReview(null);
      workspace.setIssues({});
      workspace.setTrace([]);
      workspace.setMediaTasks({});
      workspace.setConnection("blank");
      workspace.setOnboarding(true);
      return;
    }
    if (!next.project) return;
    workspace.setOnboarding(false);
    if (next.project !== workspace.project.id) {
      workspace.setReview(null);
      workspace.setIssues({});
    }
    if (
      next.forceReload
      || next.project !== workspace.project.id
      || next.run !== (workspace.run?.id || "")
      || loader.canonicalRefreshRequired.current.has(next.project)
    ) {
      void loader.loadProject(next.project, epoch);
    }
  }, [drafts, loader, state, workspace]);

  const requestNavigation = useCallback((next: {
    project: string;
    stage: PageId;
    entity?: string;
    run?: string;
    history?: "push" | "pop";
    forceReload?: boolean;
  }) => {
    const normalized: NavigationTarget = { entity: "", run: "", history: "push", forceReload: false, ...next };
    const scope = stageForPage(state.activePage);
    if (
      drafts.unsafe
      || (workspace.project.id && (workspace.project.archivedAt || workspace.project.lifecycleStatus === "archived") && findProjectDrafts(workspace.project.id).length)
    ) {
      state.setPending(normalized);
      return;
    }
    if (scope && hasDraft(workspace.project, scope)) {
      if (drafts.durableEnabled.current && workspace.project.id) {
        void drafts.flush(scope).then((saved) => {
          if (saved) applyNavigation(normalized);
          else state.setPending(normalized);
        });
        return;
      }
      state.setPending(normalized);
      return;
    }
    applyNavigation(normalized);
  }, [applyNavigation, drafts, state, workspace.project]);

  const selectRouteEntity = useCallback((entity: string) => {
    const next = { ...state.route.current, entity };
    if (next.entity === state.route.current.entity) return;
    state.route.current = next;
    writeRoute(next, "push");
    state.setRouteEntity(entity);
  }, [state]);

  const resolvePendingNavigation = useCallback(async (action: "save" | "discard" | "cancel") => {
    const pending = state.pending;
    if (!pending || action === "cancel") {
      if (pending?.history === "pop") {
        writeRoute({
          project: workspace.project.id || "",
          stage: state.activePage,
          entity: state.routeEntity,
          run: state.activePage === "trace" ? workspace.run?.id || "" : "",
        }, "replace");
      }
      state.setPending(undefined);
      return;
    }
    const scope = stageForPage(state.activePage);
    if (scope && action === "save") {
      const draft = drafts.current.current;
      if (!draft || draft.scope !== scope) {
        state.setPending(undefined);
        return;
      }
      if (scope === "brief") await drafts.commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await drafts.commitStage(scope, draft.payload);
      if (drafts.current.current) return;
    }
    if (scope) {
      discardDraft(workspace.project, scope);
      drafts.current.current = undefined;
    }
    state.setPending(undefined);
    applyNavigation(pending);
  }, [applyNavigation, drafts, state, workspace.project, workspace.run?.id]);

  useEffect(() => {
    const onPopState = () => {
      const route = routeFromLocation();
      if (
        route.project === state.route.current.project
        && route.stage === state.route.current.stage
        && route.run === state.route.current.run
      ) {
        state.route.current = route;
        state.setRouteEntity(route.entity);
        return;
      }
      requestNavigation({ ...route, history: "pop" });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [requestNavigation, state]);

  return { applyNavigation, requestNavigation, selectRouteEntity, resolvePendingNavigation };
}

function writeRoute(route: Route, action: "push" | "replace") {
  const query = new URLSearchParams();
  if (route.project) query.set("project", route.project);
  query.set("stage", route.stage);
  if (route.entity) query.set("entity", route.entity);
  if (route.run) query.set("run", route.run);
  history[`${action}State`](null, "", `${location.pathname}?${query.toString()}`);
}
