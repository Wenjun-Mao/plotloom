import { useCallback, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import { blankWorkspace, headsByStage, newClientDraftOwner, routeFromLocation, type PageId, type WorkspaceOperation } from "./contracts";
import { hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "../../workspace-state";
import type { AuthoringDraft, MediaTask, PipelineRun, ProjectResource, RunExecutionTrace, RunProgress, ServerStageName, StageEnvelope, StageHead, StoryboardReview, TraceEvent, ValidationIssue, WorkspaceProject } from "../../types";
import type { DraftRecord } from "../../draft-registry";
import { authoringDraftKey, messageFrom } from "./contracts";
import type { DraftScope } from "../../draft-registry";

export type WorkspaceRoute = ReturnType<typeof routeFromLocation>;
export type ConnectionState = "loading" | "connected" | "demo" | "blank" | "error";
export type UnsafeDraft = { record: DraftRecord; reason: "archived" | "unavailable" };

const isScope = (value: string): value is DraftScope => ["brief", "story_bible", "story_graph", "scene_beats", "storyboard"].includes(value);

/**
 * The single workspace identity and canonical snapshot owner.  Consumers may
 * request domain transitions, but cannot write individual snapshot fields.
 */
export function useWorkspaceSession() {
  const localOwner = useRef(newClientDraftOwner());
  const route = useRef(routeFromLocation());
  const epoch = useRef(0);
  const [activePage, setActivePage] = useState<PageId>(() => route.current.stage);
  const [routeEntity, setRouteEntity] = useState(() => route.current.entity);
  const [project, setProject] = useState<WorkspaceProject>(() => blankWorkspace(localOwner.current));
  const [connection, setConnection] = useState<ConnectionState>("blank");
  const [run, setRun] = useState<PipelineRun | undefined>();
  const [progress, setProgress] = useState<RunProgress | undefined>();
  const [review, setReview] = useState<StoryboardReview | null>(null);
  const [issues, setIssues] = useState<Partial<Record<ServerStageName, ValidationIssue[]>>>({});
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [executionTrace, setExecutionTrace] = useState<RunExecutionTrace | undefined>();
  const [mediaTasks, setMediaTasks] = useState<Record<string, MediaTask>>({});
  const [stageHeads, setStageHeads] = useState<Partial<Record<ServerStageName, StageHead>>>({});
  const [onboarding, setOnboarding] = useState(() => !route.current.project);
  const [unsafeDraft, setUnsafeDraft] = useState<UnsafeDraft | undefined>();
  const serverDrafts = useRef(new Map<string, AuthoringDraft>());

  const capture = useCallback((): WorkspaceOperation => ({ epoch: epoch.current, projectId: route.current.project || project.id || "", stage: activePage }), [activePage, project.id]);
  const isCurrent = useCallback((operation: WorkspaceOperation) => operation.epoch === epoch.current && operation.projectId === route.current.project && operation.stage === route.current.stage, []);
  const navigate = useCallback((next: WorkspaceRoute) => { epoch.current += 1; route.current = next; setActivePage(next.stage); setRouteEntity(next.entity); return epoch.current; }, []);
  const beginProjectLoad = useCallback(() => setConnection("loading"), []);
  const clearTrace = useCallback(() => { setTrace([]); setExecutionTrace(undefined); }, []);
  const acceptProjectLoad = useCallback(({ incoming, stages, nextRun, nextProgress, nextReview, media, drafts, message }: { incoming: ProjectResource; stages: StageEnvelope[]; nextRun: PipelineRun | undefined; nextProgress: RunProgress | undefined; nextReview: StoryboardReview | null; media: MediaTask[]; drafts: AuthoringDraft[]; message: string }) => {
    setProject((current) => ({ ...hydrateWorkspaceProject(current, incoming, stages), quarantines: quarantineItemsFromProgress(nextProgress) }));
    setStageHeads(headsByStage(stages)); setRun(nextRun); setProgress(nextProgress); setReview(nextReview); setIssues({}); clearTrace(); setMediaTasks(newestMediaTasksByShot(media));
    serverDrafts.current = new Map(drafts.filter((draft): draft is AuthoringDraft & { editorScope: DraftScope } => isScope(draft.editorScope)).map((draft) => [authoringDraftKey(incoming.id, draft.editorScope), draft]));
    setConnection("connected"); setOnboarding(false);
    return message;
  }, [clearTrace]);
  const rejectProjectLoad = useCallback((projectId: string, error: unknown, stale: UnsafeDraft | undefined) => {
    if (stale) setUnsafeDraft(stale);
    setProject(blankWorkspace(localOwner.current)); setStageHeads({}); setRun(undefined); setProgress(undefined); setReview(null); setIssues({}); clearTrace(); setMediaTasks({}); setConnection("error"); setOnboarding(false);
    return `无法加载项目 ${projectId}：${messageFrom(error)}。项目未加载；没有回退到示例。`;
  }, [clearTrace]);
  return { route, epoch, activePage, routeEntity, project, connection, run, progress, review, issues, trace, executionTrace, mediaTasks, stageHeads, onboarding, unsafeDraft, serverDrafts, capture, isCurrent, navigate, beginProjectLoad, acceptProjectLoad, rejectProjectLoad, clearTrace, setUnsafeDraft };
}
