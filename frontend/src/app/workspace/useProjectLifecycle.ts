import { useRef, useState } from "react";
import { ApiError, plotloomApi } from "../../api";
import { useConfirmation } from "../../confirmation";
import { discardDraft, hasDraft, type DraftScope } from "../../draft-registry";
import type { ReviewDraftStore } from "../../features/authoring/reviewDraftStore";
import { stageLabels } from "../../model";
import { messageFrom, stageForPage } from "./contracts";
import type { ProjectListItem, ProjectSnapshotReceipt, ServerStageName, WorkspaceProject } from "../../types";
import type { WorkspaceSession } from "./useWorkspaceSession";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";
import { useProjectDeletion } from "./useProjectDeletion";

export type LifecycleAction = "archive" | "restore" | "duplicate" | "delete" | "close" | "open" | "force_close";
type ProjectCommand = LifecycleAction | "snapshot" | "prepare_delete" | "abandon_delete";
type LifecycleSession = Pick<WorkspaceSession, "project" | "activePage" | "capture" | "isCurrent" | "acceptCanonicalProject">;
export type LifecycleTarget = Pick<ProjectListItem, "id" | "revision" | "lifecycleRevision"> & { brief: Pick<ProjectListItem["brief"], "title"> };
const commandLabels: Record<ProjectCommand, string> = {
  archive: "归档", restore: "恢复归档项目", duplicate: "复制", delete: "删除", snapshot: "创建恢复快照",
  close: "关闭", open: "重新打开", force_close: "退出工作区", abandon_delete: "核对删除条件", prepare_delete: "核对删除条件",
};

/** Owns directory lifecycle commands and the archive-after-draft decision. */
export function useProjectLifecycle({
  session,
  currentDraft,
  commitProject,
  commitStage,
  discardCurrentAuthoringDraft,
  mediaDraftQuiescence,
  reviewDraftStore,
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
  reviewDraftStore: ReviewDraftStore;
  directory: { open: () => Promise<void>; close: () => void; refresh: () => Promise<void>; setError: (error: string) => void };
  openProject: (projectId: string) => void;
  startBlank: () => void;
  explicitProjectClose: boolean;
  portableSnapshots: boolean;
  reportError: (message: string) => void;
}) {
  const duplicateKeys = useRef(new Map<string, string>());
  const [pendingArchive, setPendingArchive] = useState<{
    item: ProjectListItem; action: "archive" | "close";
    operation: ReturnType<LifecycleSession["capture"]>; scope: DraftScope;
  } | undefined>();
  const [closingProjectId, setClosingProjectId] = useState<string | undefined>();
  const [snapshottingProjectId, setSnapshottingProjectId] = useState<string | undefined>();
  const [latestSnapshot, setLatestSnapshot] = useState<ProjectSnapshotReceipt | undefined>();
  const [duplicateNotice, setDuplicateNotice] = useState("");
  const [closeNotice, setCloseNotice] = useState("");
  const commandToken = useRef<symbol | undefined>(undefined);
  const [pendingCommand, setPendingCommand] = useState<{ id: string; title: string; action: ProjectCommand }>();
  const runCommand = async (item: Pick<LifecycleTarget, "id" | "brief">, action: ProjectCommand, execute: () => Promise<void>) => {
    if (commandToken.current) return;
    const token = Symbol();
    commandToken.current = token;
    setPendingCommand({ id: item.id, title: item.brief.title || "未命名项目", action });
    setCloseNotice("");
    try { await execute(); }
    finally {
      if (commandToken.current === token) {
        commandToken.current = undefined;
        setPendingCommand(undefined);
      }
    }
  };
  const confirmation = useConfirmation(session.project.id || "directory");
  const deletion = useProjectDeletion({ session, mediaDraftQuiescence, reviewDraftStore, directory, startBlank,
    runCommand, confirmation, setClosingProjectId, setCloseNotice,
    isBusy: () => Boolean(commandToken.current || closingProjectId || snapshottingProjectId) });
  const perform = async (
    item: LifecycleTarget,
    action: LifecycleAction,
    draftDisposition?: "save" | "discard",
    openDirectoryFirst = false,
    confirmedOperation?: ReturnType<LifecycleSession["capture"]>,
  ) => {
    if ((action === "close" || action === "force_close" || action === "open") && !explicitProjectClose) return;
    const operation = confirmedOperation ?? session.capture();
    if (action === "force_close" && (item.id !== operation.projectId || !session.isCurrent(operation))) return;
    await runCommand(item, action, async () => {
      directory.setError("");
      let closeAttempt: ReturnType<ProjectDraftQuiescence["beginClose"]> | undefined;
      let reads: ReturnType<typeof plotloomApi.suspendProjectReads> | undefined;
      try {
        if (openDirectoryFirst) {
          await directory.open();
          if (!session.isCurrent(operation)) return;
        }
        if (action === "archive" && draftDisposition) {
          const scope = stageForPage(session.activePage);
          if (scope && draftDisposition === "save") {
            const draft = currentDraft.current;
            if (!draft || draft.scope !== scope) return;
            if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
            else await commitStage(scope, draft.payload);
            if (!session.isCurrent(operation) || currentDraft.current) return;
          }
          if (scope) {
            discardDraft(session.project, scope);
            currentDraft.current = undefined;
          }
          setPendingArchive(undefined);
        }
        if (action === "close" || action === "force_close" || action === "open") {
          if (action === "close" || action === "force_close") {
            // This admission begins before either disposition or drain and stays
            // active until the Close response settles. It protects the requesting
            // client from stranding a late edit behind a closed project.
            if (action === "force_close" && !session.isCurrent(operation)) return;
            closeAttempt = mediaDraftQuiescence.beginClose(item.id);
            reads = plotloomApi.suspendProjectReads(item.id);
            setClosingProjectId(item.id);
            setCloseNotice("");
            if (action === "force_close") {
              if (!session.isCurrent(operation)) return;
              await closeAttempt.discardUnsent();
              if (!await reads.settle()) throw new Error("项目读取尚未确认完成；关闭未执行，请等待读取结束后重试。");
              if (!session.isCurrent(operation)) return;
              const exitsWorkspace = operation.projectId === item.id;
              let notice = "项目已关闭，已保存内容仍可重新打开。";
              try { await plotloomApi.closeProject(item.id); }
              catch (error) {
                const busy = error instanceof ApiError && (error.details as { code?: string } | undefined)?.code === "project_busy";
                notice = busy
                  ? exitsWorkspace ? "已退出工作区；后台任务继续运行。项目尚未安全关闭，可稍后重试。" : "后台任务继续运行；项目尚未安全关闭，可稍后重试。"
                  : exitsWorkspace ? "已退出工作区，但未能确认安全关闭。已保存内容和后台任务未删除，请稍后检查项目状态。" : "未能确认项目已安全关闭。已保存内容和后台任务未删除，请稍后检查项目状态。";
              }
              finally { reads.resume(); }
              if (!session.isCurrent(operation)) return;
              if (exitsWorkspace) startBlank();
              await directory.refresh();
              setCloseNotice(notice);
              return;
            }
            const scope = stageForPage(session.activePage);
            if (draftDisposition === "discard" && (!scope || !await discardCurrentAuthoringDraft(scope))) {
              throw new Error("当前草稿未能安全丢弃；项目仍保持打开状态。");
            }
            if (!await closeAttempt.drain() || !closeAttempt.canCommit()) {
              throw new Error("编辑草稿未能保存；项目仍保持打开状态。请重试，或确认丢弃未保存修改后强制关闭。");
            }
            if (!closeAttempt.canCommit()) throw new Error("项目草稿仍在更新；请重试关闭。");
            if (!await reads.settle()) throw new Error("项目读取尚未确认完成；关闭未执行，请等待读取结束后重试。");
            if (!session.isCurrent(operation)) return;
            if (!closeAttempt.canCommit()) throw new Error("项目草稿仍在更新；请重试关闭。");
            try { await plotloomApi.closeProject(item.id); }
            finally { reads.resume(); }
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
          // The target may have retained writers even when another project/page
          // is visible. Publish authoritative admission before any resumed queue.
          mediaDraftQuiescence.setWriteAdmission(item.id,
            updated.lifecycleStatus !== "archived" && !updated.archivedAt);
          if (!session.isCurrent(operation)) return;
          if (session.project.id === item.id) session.acceptCanonicalProject({ ...session.project, ...updated });
        } else if (action === "duplicate") {
          const identity = `${item.id}:${item.lifecycleRevision ?? item.revision}`;
          let key = duplicateKeys.current.get(identity);
          if (!key) { key = `project-duplicate-${crypto.randomUUID()}`; duplicateKeys.current.set(identity, key); }
          const duplicate = await plotloomApi.duplicateProject(item.id, item.lifecycleRevision ?? item.revision, undefined, key);
          if (!session.isCurrent(operation)) return;
          duplicateKeys.current.delete(identity);
          const copied = duplicate.copiedThrough ? `项目简报及连续已就绪内容（到${stageLabels[duplicate.copiedThrough]}）` : "仅项目简报";
          const omitted = duplicate.omittedStages.map(stage => stageLabels[stage]).join("、");
          setDuplicateNotice(`已创建「${duplicate.project.brief.title}」：复制了${copied}。${omitted ? `未复制的规范阶段：${omitted}。` : ""}来源评审、图片、视频、批准和浏览器草稿未复制；原项目保持不变。`);
          directory.close();
          openProject(duplicate.project.id);
        }
        if (session.isCurrent(operation)) await directory.refresh();
      } catch (error) {
        if (session.isCurrent(operation)) directory.setError(messageFrom(error));
      } finally {
        try { reads?.resume(); }
        finally {
          try { closeAttempt?.finish(); }
          finally { if (closeAttempt) setClosingProjectId((current) => current === item.id ? undefined : current); }
        }
      }
    });
  };
  const mutate = async (item: ProjectListItem, action: LifecycleAction) => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    if (commandToken.current || closingProjectId || snapshottingProjectId) return;
    if (action === "duplicate") {
      const target = { ...item, brief: { ...item.brief } };
      confirmation.requestConfirmation({
        title: "复制简报与规范内容",
        message: "创建新项目，仅复制项目简报及从首阶段起连续已就绪的规范内容。",
        details: `${target.brief.title}\n不复制来源与大纲、角色、美术、剧本或分镜的评审记录，也不复制图片、视频、批准或浏览器草稿。原项目保持不变；完成后会列出实际复制范围。`,
        action: () => perform(target, "duplicate"),
      });
      return;
    }
    if (action === "delete") return deletion.requestDeletion(item);
    if (action === "force_close") {
      const operation = session.capture();
      if (item.id !== operation.projectId || !session.isCurrent(operation)) return;
      confirmation.requestConfirmation({
        title: "退出工作区",
        message: "丢弃本标签页尚未保存的修改；已保存内容不会删除，后台任务继续运行。",
        details: `${item.brief.title || "未命名项目"}\n如果后台任务仍在运行，只退出工作区，不解除任务占用，也不标记为已安全关闭。`,
        action: () => perform(item, "force_close", undefined, false, operation),
      });
      return;
    }
    const scope = stageForPage(session.activePage);
    if ((action === "archive" || action === "close") && item.id === session.project.id && scope && hasDraft(session.project, scope)) {
      setPendingArchive({ item, action, operation: session.capture(), scope });
      return;
    }
    await perform(item, action);
  };
  const resolvePendingArchive = async (action: "save" | "discard" | "cancel") => {
    if (commandToken.current) return;
    const pending = pendingArchive;
    if (!pending || action === "cancel") { setPendingArchive(undefined); return; }
    if (!session.isCurrent(pending.operation) || session.project.id !== pending.item.id
      || stageForPage(session.activePage) !== pending.scope) {
      setPendingArchive(undefined);
      return;
    }
    if (pending.action === "close") {
      setPendingArchive(undefined);
      await perform(pending.item, "close", action === "discard" ? "discard" : "save");
      return;
    }
    await perform(pending.item, pending.action, action);
  };
  const createSnapshot = async () => {
    const projectId = session.project.id;
    if (!portableSnapshots || !projectId || commandToken.current || mediaDraftQuiescence.isClosing(projectId)) return;
    await runCommand({ ...session.project, id: projectId }, "snapshot", async () => {
      const operation = session.capture();
      let attempt: ReturnType<ProjectDraftQuiescence["beginClose"]> | undefined;
      let reads: ReturnType<typeof plotloomApi.suspendProjectReads> | undefined;
      setSnapshottingProjectId(projectId);
      try {
        attempt = mediaDraftQuiescence.beginClose(projectId);
        reads = plotloomApi.suspendProjectReads(projectId);
        // The drain covers this requesting browser's registered queues only.
        // Another client can still have unacknowledged typing outside this copy.
        if (!await attempt.drain() || !attempt.canCommit()) {
          throw new Error("当前标签页的草稿仍在更新；未创建恢复快照。");
        }
        if (!await reads.settle()) throw new Error("项目读取尚未确认完成；未创建恢复快照，请等待读取结束后重试。");
        if (!session.isCurrent(operation)) return;
        if (!attempt.canCommit()) throw new Error("当前标签页的草稿仍在更新；未创建恢复快照。");
        let receipt: ProjectSnapshotReceipt;
        try { receipt = await plotloomApi.createProjectSnapshot(projectId); }
        finally { reads.resume(); }
        if (session.project.id === projectId) setLatestSnapshot(receipt);
      } catch (error) {
        reportError(messageFrom(error));
      } finally {
        try { reads?.resume(); }
        finally {
          try { attempt?.finish(); }
          finally { setSnapshottingProjectId((current) => current === projectId ? undefined : current); }
        }
      }
    });
  };
  const saveAndCloseCurrent = async () => {
    if (!session.project.id || commandToken.current || closingProjectId || snapshottingProjectId) return;
    const target = { ...session.project, id: session.project.id, lifecycleRevision: session.project.lifecycleRevision ?? session.project.revision };
    // Directory inspection holds a server project lease. Finish that read
    // before asking the exclusive Close gate; it must not race or erase errors.
    await perform(target, "close", "save", true);
  };
  const commandMessage = pendingCommand ? `正在${commandLabels[pendingCommand.action]}「${pendingCommand.title}」，请稍候。` : "";

  return { commandMessage, duplicateNotice, dismissDuplicateNotice: () => setDuplicateNotice(""), pendingArchive, mutate, ...deletion, resolvePendingArchive, closingProjectId, commandProjectId: pendingCommand?.id, snapshottingProjectId, latestSnapshot, createSnapshot, saveAndCloseCurrent, closeNotice, confirmation: confirmation.confirmation };
}
