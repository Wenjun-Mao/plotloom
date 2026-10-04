import { useRef, useState } from "react";
import { ApiError, plotloomApi } from "../../api";
import { useConfirmation } from "../../confirmation";
import { discardDraft, hasDraft, type DraftScope } from "../../draft-registry";
import { messageFrom, stageForPage } from "./contracts";
import type { ProjectListItem, ProjectSnapshotReceipt, ServerStageName, WorkspaceProject } from "../../types";
import type { WorkspaceSession } from "./useWorkspaceSession";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";

export type LifecycleAction = "archive" | "restore" | "duplicate" | "delete" | "close" | "open" | "force_close";
type LifecycleSession = Pick<WorkspaceSession, "project" | "activePage" | "capture" | "isCurrent" | "acceptCanonicalProject">;
type LifecycleTarget = Pick<ProjectListItem, "id" | "brief" | "revision" | "lifecycleRevision">;

/** Owns directory lifecycle commands and the archive-after-draft decision. */
export function useProjectLifecycle({
  session,
  currentDraft,
  commitProject,
  commitStage,
  discardCurrentAuthoringDraft,
  mediaDraftQuiescence,
  directory,
  openProject,
  startBlank,
  explicitProjectClose,
  portableSnapshots,
  reportError,
}: {
  session: LifecycleSession;
  currentDraft: React.MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
  commitProject: (patch: Partial<WorkspaceProject>) => Promise<void>;
  commitStage: <T>(stage: ServerStageName, content: T) => Promise<void>;
  discardCurrentAuthoringDraft: (scope: DraftScope) => Promise<boolean>;
  mediaDraftQuiescence: ProjectDraftQuiescence;
  directory: { open: () => Promise<void>; close: () => void; refresh: () => Promise<void>; setError: (error: string) => void };
  openProject: (projectId: string) => void;
  startBlank: () => void;
  explicitProjectClose: boolean;
  portableSnapshots: boolean;
  reportError: (message: string) => void;
}) {
  const duplicateKeys = useRef(new Map<string, string>());
  const [pendingArchive, setPendingArchive] = useState<{ item: ProjectListItem; action: "archive" | "close" } | undefined>();
  const [closingProjectId, setClosingProjectId] = useState<string | undefined>();
  const [snapshottingProjectId, setSnapshottingProjectId] = useState<string | undefined>();
  const [latestSnapshot, setLatestSnapshot] = useState<ProjectSnapshotReceipt | undefined>();
  const [closeNotice, setCloseNotice] = useState("");
  const confirmation = useConfirmation(session.project.id || "directory");
  const perform = async (
    item: LifecycleTarget,
    action: LifecycleAction,
    closeDraftDisposition?: "save" | "discard",
  ) => {
    const operation = session.capture();
    let closeAttempt: ReturnType<ProjectDraftQuiescence["beginClose"]> | undefined;
    try {
      if (action === "close" || action === "force_close" || action === "open") {
        if (!explicitProjectClose) return;
        if (action === "close" || action === "force_close") {
          // This admission begins before either disposition or drain and stays
          // active until the Close response settles. It protects the requesting
          // client from stranding a late edit behind a closed project.
          closeAttempt = mediaDraftQuiescence.beginClose(item.id);
          setClosingProjectId(item.id);
          setCloseNotice("");
          if (action === "force_close") {
            await closeAttempt.discardUnsent();
            const exitsWorkspace = session.project.id === item.id;
            let notice = "项目已关闭，已保存内容仍可重新打开。";
            try { await plotloomApi.closeProject(item.id); }
            catch (error) {
              const busy = error instanceof ApiError && (error.details as { code?: string } | undefined)?.code === "project_busy";
              notice = busy
                ? exitsWorkspace ? "已退出工作区；后台任务继续运行。项目尚未安全关闭，可稍后重试。" : "后台任务继续运行；项目尚未安全关闭，可稍后重试。"
                : exitsWorkspace ? "已退出工作区，但未能确认安全关闭。已保存内容和后台任务未删除，请稍后检查项目状态。" : "未能确认项目已安全关闭。已保存内容和后台任务未删除，请稍后检查项目状态。";
            }
            if (!session.isCurrent(operation)) return;
            if (exitsWorkspace) startBlank();
            await directory.refresh();
            setCloseNotice(notice);
            return;
          }
          const scope = stageForPage(session.activePage);
          if (closeDraftDisposition === "discard" && (!scope || !await discardCurrentAuthoringDraft(scope))) {
            throw new Error("当前草稿未能安全丢弃；项目仍保持打开状态。");
          }
          if (!await closeAttempt.drain() || !closeAttempt.canCommit()) {
            throw new Error("编辑草稿未能保存；项目仍保持打开状态。请重试，或确认丢弃未保存修改后强制关闭。");
          }
          if (!closeAttempt.canCommit()) throw new Error("项目草稿仍在更新；请重试关闭。");
          await plotloomApi.closeProject(item.id);
        } else {
          await plotloomApi.openProjectFolder(item.id);
          if (!session.isCurrent(operation)) return;
          directory.close();
          openProject(item.id);
          return;
        }
        if (!session.isCurrent(operation)) return;
        if (action === "close" && session.project.id === item.id) {
          // `startBlank` advances the workspace epoch. The directory has its
          // own bounded projection, so refresh it after that transition rather
          // than leaving the just-closed item painted as active.
          startBlank();
          await directory.refresh();
          return;
        }
      } else if (action === "archive" || action === "restore") {
        const updated = action === "archive"
          ? await plotloomApi.archiveProject(item.id, item.lifecycleRevision ?? item.revision)
          : await plotloomApi.restoreProject(item.id, item.lifecycleRevision ?? item.revision);
        if (!session.isCurrent(operation)) return;
        if (session.project.id === item.id) session.acceptCanonicalProject({ ...session.project, ...updated });
      } else if (action === "duplicate") {
        const identity = `${item.id}:${item.lifecycleRevision ?? item.revision}`;
        let key = duplicateKeys.current.get(identity);
        if (!key) { key = `project-duplicate-${crypto.randomUUID()}`; duplicateKeys.current.set(identity, key); }
        const duplicate = await plotloomApi.duplicateProject(item.id, item.lifecycleRevision ?? item.revision, undefined, key);
        if (!session.isCurrent(operation)) return;
        duplicateKeys.current.delete(identity);
        directory.close();
        openProject(duplicate.project.id);
      } else {
        const title = item.brief.title || item.id;
        const confirmed = window.prompt(`输入完整片名“${title}”以永久删除`, "");
        if (confirmed !== title) { directory.setError("片名不匹配；未发送永久删除请求。"); return; }
        await plotloomApi.permanentlyDeleteProject(item.id, item.lifecycleRevision ?? item.revision, confirmed);
        if (!session.isCurrent(operation)) return;
        if (session.project.id === item.id) startBlank();
      }
      if (session.isCurrent(operation)) await directory.refresh();
    } catch (error) {
      if (session.isCurrent(operation)) directory.setError(messageFrom(error));
    } finally {
      closeAttempt?.finish();
      if (closeAttempt) setClosingProjectId((current) => current === item.id ? undefined : current);
    }
  };
  const mutate = async (item: ProjectListItem, action: LifecycleAction) => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    if (closingProjectId || snapshottingProjectId) return;
    if (action === "force_close") {
      confirmation.requestConfirmation({
        title: "强制关闭项目",
        message: "丢弃本标签页尚未保存的修改；已保存内容不会删除，后台任务继续运行。",
        details: `${item.brief.title || "未命名项目"}\n如果后台任务仍在运行，只退出工作区，不解除任务占用，也不标记为已安全关闭。`,
        action: () => perform(item, "force_close"),
      });
      return;
    }
    const scope = stageForPage(session.activePage);
    if ((action === "archive" || action === "close") && item.id === session.project.id && scope && hasDraft(session.project, scope)) { setPendingArchive({ item, action }); return; }
    await perform(item, action);
  };
  const resolvePendingArchive = async (action: "save" | "discard" | "cancel") => {
    const pending = pendingArchive;
    if (!pending || action === "cancel") { setPendingArchive(undefined); return; }
    const scope = stageForPage(session.activePage);
    if (pending.action === "close") {
      setPendingArchive(undefined);
      await perform(pending.item, "close", action === "discard" ? "discard" : "save");
      return;
    }
    if (scope && action === "save") {
      const draft = currentDraft.current;
      if (!draft || draft.scope !== scope) { setPendingArchive(undefined); return; }
      if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await commitStage(scope, draft.payload);
      if (currentDraft.current) return;
    }
    if (scope) {
      discardDraft(session.project, scope);
      currentDraft.current = undefined;
    }
    setPendingArchive(undefined);
    await perform(pending.item, pending.action);
  };
  const createSnapshot = async () => {
    const projectId = session.project.id;
    if (!portableSnapshots || !projectId || mediaDraftQuiescence.isClosing(projectId)) return;
    const attempt = mediaDraftQuiescence.beginClose(projectId);
    setSnapshottingProjectId(projectId);
    try {
      // The drain covers this requesting browser's registered queues only.
      // Another client can still have unacknowledged typing outside this copy.
      if (!await attempt.drain() || !attempt.canCommit()) {
        throw new Error("当前标签页的草稿仍在更新；未创建恢复快照。");
      }
      const receipt = await plotloomApi.createProjectSnapshot(projectId);
      if (session.project.id === projectId) setLatestSnapshot(receipt);
    } catch (error) {
      reportError(messageFrom(error));
    } finally {
      attempt.finish();
      setSnapshottingProjectId((current) => current === projectId ? undefined : current);
    }
  };
  const saveAndCloseCurrent = async () => {
    if (!session.project.id || closingProjectId || snapshottingProjectId) return;
    const operation = session.capture();
    const target = { ...session.project, id: session.project.id, lifecycleRevision: session.project.lifecycleRevision ?? session.project.revision };
    // Directory inspection holds a server project lease. Finish that read
    // before asking the exclusive Close gate; it must not race or erase errors.
    await directory.open();
    if (!session.isCurrent(operation)) return;
    await perform(target, "close", "save");
  };
  return { pendingArchive, mutate, resolvePendingArchive, closingProjectId, snapshottingProjectId, latestSnapshot, createSnapshot, saveAndCloseCurrent, closeNotice, confirmation: confirmation.confirmation };
}
