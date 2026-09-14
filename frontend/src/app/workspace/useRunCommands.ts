import { useCallback, useRef } from "react";
import { plotloomApi } from "../../api";
import { providerSessionKeys } from "../../session-key";
import { stageForPage, type WorkspaceOperation, type PageId } from "./contracts";
import type { PipelineRun, QuarantineItem, ServerStageName, TextProviderProfileView, WorkspaceProject } from "../../types";

type Currentness = { capture: () => WorkspaceOperation; isCurrent: (operation: WorkspaceOperation) => boolean };
type ProfileCommands = {
  draft: TextProviderProfileView;
  sessionKey: string;
  loaded: React.MutableRefObject<boolean>;
  refresh: () => Promise<{ profiles: TextProviderProfileView[]; activeProfileId: string }>;
  save: (draft: TextProviderProfileView, key: string) => Promise<TextProviderProfileView>;
  ensureFrozenCredential: (run: PipelineRun) => Promise<boolean>;
};

/** Commands that spend, resume, cancel, repair, or observe one pipeline run. */
export function useRunCommands({ project, activePage, run, profiles, currentness, pollRun, openTrace, setRun, setBusy, setError, hasDraft }: {
  project: WorkspaceProject;
  activePage: PageId;
  run?: PipelineRun;
  profiles: ProfileCommands;
  currentness: Currentness;
  pollRun: (runId: string, projectId?: string) => Promise<void>;
  openTrace: (run: PipelineRun) => void;
  setRun: React.Dispatch<React.SetStateAction<PipelineRun | undefined>>;
  setBusy: (busy: boolean) => void;
  setError: (message: string) => void;
  hasDraft: (scope: ReturnType<typeof stageForPage>) => boolean;
}) {
  const repairKeys = useRef(new Map<string, string>());
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
  const cancelRun = useCallback(async () => {
    if (!run) return;
    const operation = currentness.capture();
    try { const cancelled = await plotloomApi.cancelRun(run.id); if (!currentness.isCurrent(operation)) return; setRun(cancelled); void pollRun(cancelled.id, cancelled.projectId).catch((error) => setError(describeError(error))); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
  }, [currentness, pollRun, run, setError, setRun]);
  const resumeRun = useCallback(async () => {
    if (!run || (run.status !== "queued" && run.status !== "running")) return;
    if (!await profiles.ensureFrozenCredential(run)) return;
    const operation = currentness.capture();
    try { const profileId = String(run.providerSnapshot.profileId || "default"); const resumed = await plotloomApi.resumeRun(run.id, profileId, run.providerSnapshot.textAuthMode !== "none"); if (!currentness.isCurrent(operation)) return; setRun(resumed); void pollRun(run.id).catch((error) => setError(describeError(error))); }
    catch (error) { if (currentness.isCurrent(operation)) setError(describeError(error)); }
  }, [currentness, pollRun, profiles, run, setError, setRun]);
  const repair = useCallback(async (item: QuarantineItem) => {
    if (!run || !item.repairEligible) { setError("这个 work unit 当前不具备精确修复资格。"); return; }
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
  return { startRun, cancelRun, resumeRun, repair, rebuild };
}
