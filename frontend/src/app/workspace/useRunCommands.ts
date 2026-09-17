import { useCallback, useRef } from "react";
import { plotloomApi } from "../../api";
import { providerSessionKeys } from "../../session-key";
import { headsByStage, stageForPage, type WorkspaceOperation } from "./contracts";
import type { PipelineRun, QuarantineItem, ServerStageName, TextProviderProfileView } from "../../types";
import type { WorkspaceSession } from "./useWorkspaceSession";

type Currentness = { capture: () => WorkspaceOperation; isCurrent: (operation: WorkspaceOperation) => boolean };
type RunCommandSession = Pick<WorkspaceSession, "project" | "activePage" | "run" | "route" | "capture" | "isCurrent" | "acceptRun">;
type ProfileCommands = {
  draft: TextProviderProfileView;
  sessionKey: string;
  loaded: React.MutableRefObject<boolean>;
  refresh: () => Promise<{ profiles: TextProviderProfileView[]; activeProfileId: string }>;
  save: (draft: TextProviderProfileView, key: string) => Promise<TextProviderProfileView>;
  ensureFrozenCredential: (run: PipelineRun) => Promise<boolean>;
};

/** Commands that spend, resume, cancel, repair, or observe one pipeline run. */
export function useRunCommands({ session, profiles, pollRun, openTrace, setBusy, setError, hasDraft }: {
  session: RunCommandSession;
  profiles: ProfileCommands;
  pollRun: (runId: string, projectId?: string) => Promise<void>;
  openTrace: (run: PipelineRun) => void;
  setBusy: (busy: boolean) => void;
  setError: (message: string) => void;
  hasDraft: (scope: ReturnType<typeof stageForPage>) => boolean;
}) {
  const repairKeys = useRef(new Map<string, string>());
  const { project, activePage, run } = session;
  const currentness: Currentness = { capture: session.capture, isCurrent: session.isCurrent };
  const isSelectedRun = (candidate: PipelineRun | undefined): candidate is PipelineRun => Boolean(candidate && (!session.route.run || session.route.run === candidate.id));
  const describeError = (error: unknown) => error instanceof Error ? error.message : "未知错误";
  const prepareProfile = useCallback(async (): Promise<TextProviderProfileView> => {
    let draft = profiles.draft;
    let key = profiles.sessionKey;
    if (!profiles.loaded.current) {
      const catalog = await profiles.refresh();
      draft = catalog.profiles.find((profile) => profile.profileId === catalog.activeProfileId) || draft;
      key = providerSessionKeys.read(draft.profileId);
    }
    return profiles.save(draft, key);
  }, [profiles]);
  const startRun = useCallback(async (stages: ServerStageName[]) => {
    if (!project.id) { setError("请先保存项目，再启动生成流水线。"); return; }
    if (profiles.draft.enabled === false) { setError("当前活动 Profile 已停用；请先在设置中启用可用 Profile。不会自动切换后端。"); return; }
    const operation = currentness.capture(); setBusy(true); setError("");
    try { const saved = await prepareProfile(); if (!currentness.isCurrent(operation)) return; const started = await plotloomApi.startRun(project.id, stages, saved.profileId, saved.configuration.textAuthMode === "bearer"); if (currentness.isCurrent(operation)) openTrace(started); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
    finally { if (currentness.isCurrent(operation)) setBusy(false); }
  }, [currentness, openTrace, prepareProfile, profiles.draft.enabled, project.id, setBusy, setError]);
  const startProposal = useCallback(async (projectId: string) => {
    if (!projectId) { setError("请先保存梗概，再生成故事提案。"); return; }
    if (profiles.draft.enabled === false) { setError("当前活动 Profile 已停用；请先在设置中启用可用 Profile。不会自动切换后端。"); return; }
    const operation = currentness.capture(); setBusy(true); setError("");
    try {
      // Resolve the canonical heads after the Brief save, not from this hook's
      // pre-save render. This keeps a Bible refinement eligible for Graph-only
      // regeneration instead of treating it as an obsolete proposal snapshot.
      const heads = headsByStage((await plotloomApi.getStages(projectId)).stages);
      if (!currentness.isCurrent(operation)) return;
      const bibleCurrent = heads.story_bible?.status === "ready";
      const graphCurrent = heads.story_graph?.status === "ready";
      const stages: ServerStageName[] = !bibleCurrent
        ? ["story_bible", "story_graph"]
        : !graphCurrent
          ? ["story_graph"]
          : [];
      if (!stages.length) {
        setError("当前故事提案已经是最新版本；可直接细化内容或进入分镜规划。");
        return;
      }
      const saved = await prepareProfile();
      if (!currentness.isCurrent(operation)) return;
      const started = await plotloomApi.startRun(projectId, stages, saved.profileId, saved.configuration.textAuthMode === "bearer");
      if (!currentness.isCurrent(operation)) return;
      // A proposal is a review of these two existing stages, not a new run type
      // or a transition into scenes/storyboard. Keep the user in that review.
      session.acceptRun(started);
      await pollRun(started.id, projectId);
    } catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
    finally { if (currentness.isCurrent(operation)) setBusy(false); }
  }, [currentness, pollRun, prepareProfile, profiles.draft.enabled, session, setBusy, setError]);
  const startStoryboard = useCallback(async (projectId: string) => {
    if (!projectId) { setError("请先保存并审阅故事提案，再生成场景与分镜。"); return; }
    if (profiles.draft.enabled === false) { setError("当前活动 Profile 已停用；请先在设置中启用可用 Profile。不会自动切换后端。"); return; }
    const operation = currentness.capture(); setBusy(true); setError("");
    try {
      // Resolve heads at click time. The proposal owns Bible/Graph; this
      // continuation may only fill its downstream missing or stale range.
      const heads = headsByStage((await plotloomApi.getStages(projectId)).stages);
      if (!currentness.isCurrent(operation)) return;
      if (heads.story_bible?.status !== "ready" || heads.story_graph?.status !== "ready") {
        setError("故事提案已过期或不完整；请先重新生成 Story Bible 与剧情 DAG。");
        return;
      }
      const stages: ServerStageName[] = heads.scene_beats?.status !== "ready"
        ? ["scene_beats", "storyboard"]
        : heads.storyboard?.status !== "ready"
          ? ["storyboard"]
          : [];
      if (!stages.length) {
        setError("场景与分镜已经是最新版本；不会创建替换运行。");
        return;
      }
      const saved = await prepareProfile();
      if (!currentness.isCurrent(operation)) return;
      const started = await plotloomApi.startRun(projectId, stages, saved.profileId, saved.configuration.textAuthMode === "bearer");
      if (!currentness.isCurrent(operation)) return;
      session.acceptRun(started);
      await pollRun(started.id, projectId);
    } catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
    finally { if (currentness.isCurrent(operation)) setBusy(false); }
  }, [currentness, pollRun, prepareProfile, profiles.draft.enabled, session, setBusy, setError]);
  const cancelRun = useCallback(async () => {
    if (!isSelectedRun(run)) return;
    const operation = currentness.capture();
    try { const cancelled = await plotloomApi.cancelRun(run.id); if (!currentness.isCurrent(operation)) return; session.acceptRun(cancelled); void pollRun(cancelled.id, cancelled.projectId).catch((error) => setError(describeError(error))); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
  }, [currentness, pollRun, run, session, setError]);
  const resumeRun = useCallback(async () => {
    if (!isSelectedRun(run) || (run.status !== "queued" && run.status !== "running")) return;
    if (!await profiles.ensureFrozenCredential(run)) return;
    const operation = currentness.capture();
    try { const profileId = String(run.providerSnapshot.profileId || "default"); const resumed = await plotloomApi.resumeRun(run.id, profileId, run.providerSnapshot.textAuthMode !== "none"); if (!currentness.isCurrent(operation)) return; session.acceptRun(resumed); void pollRun(run.id).catch((error) => setError(describeError(error))); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
  }, [currentness, pollRun, profiles, run, session, setError]);
  const repair = useCallback(async (item: QuarantineItem) => {
    if (!isSelectedRun(run) || !item.repairEligible) { setError("这个 work unit 当前不具备精确修复资格。"); return; }
    if (!await profiles.ensureFrozenCredential(run)) return;
    const operation = currentness.capture(); setBusy(true);
    try { const profileId = String(run.providerSnapshot.profileId || "default"); const identity = `${run.id}:${item.id}`; let key = repairKeys.current.get(identity); if (!key) { key = `work-unit-repair-${crypto.randomUUID()}`; repairKeys.current.set(identity, key); } const next = await plotloomApi.repairWorkUnit(run.id, item.id, profileId, key, run.providerSnapshot.textAuthMode !== "none"); if (!currentness.isCurrent(operation)) return; repairKeys.current.delete(identity); openTrace(next); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
    finally { if (currentness.isCurrent(operation)) setBusy(false); }
  }, [currentness, openTrace, profiles, run, setBusy, setError]);
  const rebuild = useCallback(async (fromStage: ServerStageName) => {
    if (!project.id) { setError("请先保存项目，再重建下游阶段。"); return; }
    if (hasDraft(stageForPage(activePage))) { setError("请先保存或丢弃当前阶段草稿，再创建重建运行。"); return; }
    const operation = currentness.capture(); setBusy(true);
    try { const saved = await prepareProfile(); if (!currentness.isCurrent(operation)) return; const next = await plotloomApi.rebuild(project.id, fromStage, saved.profileId, saved.configuration.textAuthMode === "bearer"); if (currentness.isCurrent(operation)) openTrace(next); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
    finally { if (currentness.isCurrent(operation)) setBusy(false); }
  }, [activePage, currentness, hasDraft, openTrace, prepareProfile, project.id, setBusy, setError]);
  return { startRun, startProposal, startStoryboard, cancelRun, resumeRun, repair, rebuild };
}
