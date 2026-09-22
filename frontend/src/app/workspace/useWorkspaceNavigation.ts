import { useCallback, useEffect, useState } from "react";
import { discardDraft, findProjectDrafts, hasDraft, type DraftScope } from "../../draft-registry";
import type { PipelineRun, ServerStageName, WorkspaceProject } from "../../types";
import { routeFromLocation, stageForPage, type NavigationTarget, type PageId } from "./contracts";
import type { UnsafeDraft, WorkspaceSession } from "./useWorkspaceSession";

type NavigationSession = Pick<WorkspaceSession,
  "activePage" | "project" | "run" | "runSelectionPending" | "unsafeDraft" | "routeRef" | "setUnsafeDraft"
  | "clearForEmptyRoute" | "navigate" | "navigateToProject" | "needsCanonicalRefresh"
  | "focusEntity" | "updateRouteHash" | "navigateHash" | "replaceCurrentRoute" | "acceptRun" | "beginRunSelection" | "cancelRunSelection" | "clearTrace"
>;

interface WorkspaceNavigationInput {
  session: NavigationSession;
  drafts: {
    current: React.MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
    durableEnabled: React.MutableRefObject<boolean>;
    flush: (scope: DraftScope) => Promise<boolean>;
    commitProject: (patch: Partial<WorkspaceProject>) => Promise<void>;
    commitStage: <T>(stage: ServerStageName, content: T) => Promise<void>;
    clearRecovery: () => void;
    clearConflict: () => void;
  };
  loadProject: (projectId: string, epoch?: number) => Promise<void>;
  pollRun: (runId: string, projectId?: string) => Promise<void>;
  isProjectClosing: (projectId: string) => boolean;
}

/**
 * Owns URL/history writes and draft-gated route changes. The session is the
 * only authority that increments epochs or mutates canonical route identity.
 */
export function useWorkspaceNavigation({ session, drafts, loadProject, pollRun, isProjectClosing }: WorkspaceNavigationInput) {
  const [pendingNavigation, setPendingNavigation] = useState<NavigationTarget | undefined>();

  const clearDraftRouteState = useCallback(() => {
    drafts.current.current = undefined;
    drafts.clearRecovery();
    drafts.clearConflict();
    session.setUnsafeDraft(undefined);
  }, [drafts, session]);

  const applyNavigation = useCallback((next: NavigationTarget) => {
    const route = { project: next.project, stage: next.stage, entity: next.entity, run: next.run, hash: next.hash };
    const historyMode = next.history === "push" ? "push" : "none";
    const previousRoute = session.routeRef.current;
    clearDraftRouteState();
    if (!next.project) {
      // A blank or demo workspace has no server ID. Moving between its pages
      // must retain that local snapshot; only leaving a loaded project opens a
      // new blank onboarding workspace.
      if (next.project !== (session.project.id || "")) session.clearForEmptyRoute(route, historyMode);
      else session.navigate(route, historyMode);
      return;
    }
    const traceSelectionRequested = next.stage === "trace" && (
      next.run !== (session.run?.id || "")
      || session.runSelectionPending
      || (previousRoute.stage !== "trace" && !next.run)
    );
    const epoch = session.navigateToProject(route, historyMode);
    if (next.stage !== "trace") session.cancelRunSelection();
    else if (traceSelectionRequested) session.beginRunSelection(next.run);
    if (
      next.forceReload
      || next.project !== session.project.id
      || traceSelectionRequested
      || session.needsCanonicalRefresh(next.project)
    ) {
      void loadProject(next.project, epoch);
    }
  }, [clearDraftRouteState, loadProject, session]);

  const requestNavigation = useCallback((next: {
    project: string;
    stage: PageId;
    entity?: string;
    run?: string;
    hash?: string;
    history?: "push" | "pop";
    forceReload?: boolean;
  }) => {
    const normalized: NavigationTarget = { entity: "", run: "", hash: "", history: "push", forceReload: false, ...next };
    const currentRoute = session.routeRef.current;
    if (
      normalized.project === currentRoute.project
      && normalized.stage === currentRoute.stage
      && normalized.entity === currentRoute.entity
      && normalized.run === currentRoute.run
      && !normalized.forceReload
    ) {
      if (normalized.hash !== currentRoute.hash) {
        if (normalized.history === "push") session.navigateHash(normalized.hash);
        else session.updateRouteHash(normalized.hash);
      }
      return;
    }
    if (session.project.id && isProjectClosing(session.project.id)) {
      // A history pop already changed the address; restore the admitted route
      // rather than unmounting a writer during Close.
      if (normalized.history === "pop") session.replaceCurrentRoute();
      return;
    }
    const scope = stageForPage(session.activePage);
    const unsafeDraft: UnsafeDraft | undefined = session.unsafeDraft;
    if (
      unsafeDraft
      || (session.project.id && (session.project.archivedAt || session.project.lifecycleStatus === "archived") && findProjectDrafts(session.project.id).length)
    ) {
      setPendingNavigation(normalized);
      return;
    }
    if (scope && hasDraft(session.project, scope)) {
      if (drafts.durableEnabled.current && session.project.id) {
        void drafts.flush(scope).then((saved) => {
          if (saved) applyNavigation(normalized);
          else setPendingNavigation(normalized);
        });
        return;
      }
      setPendingNavigation(normalized);
      return;
    }
    applyNavigation(normalized);
  }, [applyNavigation, drafts, isProjectClosing, session]);

  const selectRouteEntity = useCallback((entity: string) => session.focusEntity(entity), [session]);
  const openRunTrace = useCallback((run: PipelineRun) => {
    if (isProjectClosing(run.projectId)) return;
    clearDraftRouteState();
    session.navigateToProject({ project: run.projectId, stage: "trace", entity: "", run: run.id, hash: "" }, "push");
    session.acceptRun(run);
    session.clearTrace();
    void pollRun(run.id, run.projectId);
  }, [clearDraftRouteState, isProjectClosing, pollRun, session]);

  const resolvePendingNavigation = useCallback(async (action: "save" | "discard" | "cancel") => {
    const pending = pendingNavigation;
    if (!pending || action === "cancel") {
      if (pending?.history === "pop") session.replaceCurrentRoute();
      setPendingNavigation(undefined);
      return;
    }
    const scope = stageForPage(session.activePage);
    if (scope && action === "save") {
      const draft = drafts.current.current;
      if (!draft || draft.scope !== scope) {
        setPendingNavigation(undefined);
        return;
      }
      if (scope === "brief") await drafts.commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await drafts.commitStage(scope, draft.payload);
      if (drafts.current.current) return;
    }
    if (scope) {
      discardDraft(session.project, scope);
      drafts.current.current = undefined;
    }
    setPendingNavigation(undefined);
    applyNavigation(pending);
  }, [applyNavigation, drafts, pendingNavigation, session]);
  const continueAfterUnsafeDraft = useCallback(() => {
    if (!pendingNavigation) return;
    setPendingNavigation(undefined);
    applyNavigation(pendingNavigation);
  }, [applyNavigation, pendingNavigation]);

  useEffect(() => {
    const onPopState = () => {
      const route = routeFromLocation();
      const current = session.routeRef.current;
      if (route.project === current.project && route.stage === current.stage && route.run === current.run) {
        session.focusEntity(route.entity);
        session.updateRouteHash(route.hash);
        return;
      }
      requestNavigation({ ...route, history: "pop" });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [requestNavigation, session]);

  useEffect(() => {
    const onHashChange = () => {
      const route = routeFromLocation();
      const current = session.routeRef.current;
      if (route.project === current.project && route.stage === current.stage && route.entity === current.entity && route.run === current.run) session.updateRouteHash(route.hash);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [session]);

  return { applyNavigation, requestNavigation, selectRouteEntity, openRunTrace, pendingNavigation, resolvePendingNavigation, continueAfterUnsafeDraft };
}
