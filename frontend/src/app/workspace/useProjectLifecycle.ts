import { useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { useConfirmation } from "../../confirmation";
import type { DraftScope } from "../../draft-registry";
import type { ReviewDraftStore } from "../../features/authoring/reviewDraftStore";
import { stageLabels } from "../../model";
import { messageFrom } from "./contracts";
import type { ProjectListItem, ProjectSnapshotReceipt, ServerStageName, WorkspaceProject } from "../../types";
import type { WorkspaceSession } from "./useWorkspaceSession";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";
import { useProjectDeletion } from "./useProjectDeletion";

export type LifecycleAction = "archive" | "restore" | "duplicate" | "delete" | "freeze" | "unfreeze";
type ProjectCommand = LifecycleAction | "snapshot" | "prepare_delete" | "abandon_delete";
type LifecycleSession = Pick<WorkspaceSession, "project" | "activePage" | "capture" | "isCurrent" | "acceptCanonicalProject">;
export type LifecycleTarget = Pick<ProjectListItem, "id" | "revision" | "lifecycleRevision"> & { brief: Pick<ProjectListItem["brief"], "title"> };
const commandLabels: Record<ProjectCommand, string> = {
  archive: "归档", restore: "恢复归档项目", duplicate: "复制", delete: "删除", snapshot: "创建恢复快照",
  freeze: "冻结", unfreeze: "解除冻结", abandon_delete: "核对删除条件", prepare_delete: "核对删除条件",
};
type Input = {
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
};

/** Saving working input, project admission and navigation have separate owners. */
export function useProjectLifecycle({ session, mediaDraftQuiescence, reviewDraftStore, directory, openProject, startBlank,
  explicitProjectClose, portableSnapshots, reportError }: Input) {
  const duplicateKeys = useRef(new Map<string, string>());
  const commandToken = useRef<symbol | undefined>(undefined);
  const [closingProjectId, setClosingProjectId] = useState<string>();
  const [snapshottingProjectId, setSnapshottingProjectId] = useState<string>();
  const [latestSnapshot, setLatestSnapshot] = useState<ProjectSnapshotReceipt>();
  const [duplicateNotice, setDuplicateNotice] = useState("");
  const [closeNotice, setCloseNotice] = useState("");
  const [pendingCommand, setPendingCommand] = useState<{ id: string; title: string; action: ProjectCommand }>();
  const runCommand = async (item: Pick<LifecycleTarget, "id" | "brief">, action: ProjectCommand, execute: () => Promise<void>) => {
    if (commandToken.current) return;
    const token = Symbol(); commandToken.current = token;
    setPendingCommand({ id: item.id, title: item.brief.title || "未命名项目", action }); setCloseNotice("");
    try { await execute(); }
    finally { if (commandToken.current === token) { commandToken.current = undefined; setPendingCommand(undefined); } }
  };
  const confirmation = useConfirmation(session.project.id || "directory");
  const deletion = useProjectDeletion({ session, mediaDraftQuiescence, reviewDraftStore, directory, startBlank,
    runCommand, confirmation, setClosingProjectId, setCloseNotice,
    isBusy: () => Boolean(commandToken.current || closingProjectId || snapshottingProjectId) });

  const withQuiescentInputs = async (projectId: string, execute: () => Promise<void>) => {
    const attempt = mediaDraftQuiescence.beginClose(projectId);
    const reads = plotloomApi.suspendProjectReads(projectId);
    try {
      // Exclusive transitions require server receipts. A local journal suffices
      // for navigation, but cannot establish a stable project folder.
      if (!await attempt.drain() || !attempt.canCommit()) throw new Error("编辑输入尚未同步到项目，操作未执行；请重试。");
      if (!await reads.settle()) throw new Error("项目读取尚未完成；请稍后重试。");
      if (!attempt.canCommit()) throw new Error("项目输入仍在更新；请稍后重试。");
      await execute();
    } finally { reads.resume(); attempt.finish(); }
  };
  const perform = async (item: LifecycleTarget, action: LifecycleAction) => {
    const operation = session.capture();
    await runCommand(item, action, async () => {
      directory.setError("");
      try {
        if (action === "freeze" || action === "unfreeze") {
          if (!explicitProjectClose) return;
          setClosingProjectId(item.id);
          if (action === "freeze") await withQuiescentInputs(item.id, async () => { await plotloomApi.freezeProject(item.id); });
          else await plotloomApi.unfreezeProject(item.id);
          mediaDraftQuiescence.setWriteAdmission(item.id, action === "unfreeze" && session.project.lifecycleStatus !== "archived");
          if (session.isCurrent(operation) && session.project.id === item.id) session.acceptCanonicalProject({ ...session.project, operationalState: action === "freeze" ? "closed" : "open" });
          setCloseNotice(action === "freeze" ? "项目已冻结；可只读浏览和播放已就绪内容。" : "已解除冻结；不会应用草稿或重新启动任务。");
        } else if (action === "archive" || action === "restore") {
          let updated;
          if (action === "archive") await withQuiescentInputs(item.id, async () => { updated = await plotloomApi.archiveProject(item.id, item.lifecycleRevision ?? item.revision); });
          else updated = await plotloomApi.restoreProject(item.id, item.lifecycleRevision ?? item.revision);
          if (updated) {
            mediaDraftQuiescence.setWriteAdmission(item.id, updated.lifecycleStatus !== "archived" && !updated.archivedAt && updated.operationalState !== "closed");
            if (session.isCurrent(operation) && session.project.id === item.id) session.acceptCanonicalProject({ ...session.project, ...updated });
          }
        } else if (action === "duplicate") {
          const identity = `${item.id}:${item.lifecycleRevision ?? item.revision}`;
          let key = duplicateKeys.current.get(identity);
          if (!key) { key = `project-duplicate-${crypto.randomUUID()}`; duplicateKeys.current.set(identity, key); }
          const duplicate = await plotloomApi.duplicateProject(item.id, item.lifecycleRevision ?? item.revision, undefined, key);
          duplicateKeys.current.delete(identity);
          const copied = duplicate.copiedThrough ? `简报及连续已就绪内容（到${stageLabels[duplicate.copiedThrough]}）` : duplicate.project.hasConfirmedBrief === false ? "空白项目身份" : "项目简报";
          setDuplicateNotice(`已创建「${duplicate.project.displayTitle || duplicate.project.brief.title || "未命名项目"}」：复制了${copied}。媒体、批准、任务与编辑草稿未复制。`);
          if (session.isCurrent(operation)) { directory.close(); openProject(duplicate.project.id); }
        }
        await directory.refresh();
      } catch (error) { if (session.isCurrent(operation)) directory.setError(messageFrom(error)); }
      finally { setClosingProjectId(undefined); }
    });
  };
  const mutate = async (item: ProjectListItem, action: LifecycleAction) => {
    if (commandToken.current || closingProjectId || snapshottingProjectId) return;
    if (action === "delete") return deletion.requestDeletion(item);
    if (action === "duplicate") {
      const target = { ...item, brief: { ...item.brief } };
      confirmation.requestConfirmation({ title: "复制简报与规范内容", message: "创建新项目，仅复制已确认简报及连续已就绪的规范内容。",
        details: `${target.brief.title}\n媒体、批准、任务与编辑草稿不复制。`, action: () => perform(target, action) }); return;
    }
    await perform(item, action);
  };
  const createSnapshot = async () => {
    const projectId = session.project.id;
    if (!portableSnapshots || !projectId || commandToken.current) return;
    await runCommand({ ...session.project, id: projectId }, "snapshot", async () => {
      setSnapshottingProjectId(projectId);
      try { await withQuiescentInputs(projectId, async () => { setLatestSnapshot(await plotloomApi.createProjectSnapshot(projectId)); }); }
      catch (error) { reportError(messageFrom(error)); }
      finally { setSnapshottingProjectId(undefined); }
    });
  };
  const commandMessage = pendingCommand ? `正在${commandLabels[pendingCommand.action]}「${pendingCommand.title}」，请稍候。` : "";
  return { commandMessage, duplicateNotice, dismissDuplicateNotice: () => setDuplicateNotice(""), mutate, ...deletion,
    closingProjectId, commandProjectId: pendingCommand?.id, snapshottingProjectId, latestSnapshot, createSnapshot,
    closeNotice, confirmation: confirmation.confirmation };
}
