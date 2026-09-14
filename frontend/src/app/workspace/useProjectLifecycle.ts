import { useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { plotloomApi } from "../../api";
import { discardDraft, hasDraft, type DraftScope } from "../../draft-registry";
import { messageFrom, stageForPage, type PageId, type WorkspaceOperation } from "./contracts";
import type { ProjectListItem, ServerStageName, WorkspaceProject } from "../../types";

type LifecycleAction = "archive" | "restore" | "duplicate" | "delete";

/** Owns directory lifecycle commands and the archive-after-draft decision. */
export function useProjectLifecycle({ project, activePage, currentDraft, commitProject, commitStage, capture, isCurrent, setProject, directory, openProject, startBlank }: {
  project: WorkspaceProject;
  activePage: PageId;
  currentDraft: MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
  commitProject: (patch: Partial<WorkspaceProject>) => Promise<void>;
  commitStage: <T>(stage: ServerStageName, content: T) => Promise<void>;
  capture: () => WorkspaceOperation;
  isCurrent: (operation: WorkspaceOperation) => boolean;
  setProject: Dispatch<SetStateAction<WorkspaceProject>>;
  directory: { setOpen: (open: boolean) => void; refresh: () => Promise<void>; setError: (error: string) => void };
  openProject: (projectId: string) => void;
  startBlank: () => void;
}) {
  const duplicateKeys = useRef(new Map<string, string>());
  const [pendingArchive, setPendingArchive] = useState<ProjectListItem | undefined>();
  const perform = async (item: ProjectListItem, action: LifecycleAction) => {
    const operation = capture();
    try {
      if (action === "archive" || action === "restore") {
        const updated = action === "archive"
          ? await plotloomApi.archiveProject(item.id, item.lifecycleRevision ?? item.revision)
          : await plotloomApi.restoreProject(item.id, item.lifecycleRevision ?? item.revision);
        if (!isCurrent(operation)) return;
        if (project.id === item.id) setProject((current) => ({ ...current, ...updated }));
      } else if (action === "duplicate") {
        const identity = `${item.id}:${item.lifecycleRevision ?? item.revision}`;
        let key = duplicateKeys.current.get(identity);
        if (!key) { key = `project-duplicate-${crypto.randomUUID()}`; duplicateKeys.current.set(identity, key); }
        const duplicate = await plotloomApi.duplicateProject(item.id, item.lifecycleRevision ?? item.revision, undefined, key);
        if (!isCurrent(operation)) return;
        duplicateKeys.current.delete(identity);
        directory.setOpen(false);
        openProject(duplicate.project.id);
      } else {
        const title = item.brief.title || item.id;
        const confirmed = window.prompt(`输入完整片名“${title}”以永久删除`, "");
        if (confirmed !== title) { directory.setError("片名不匹配；未发送永久删除请求。"); return; }
        await plotloomApi.permanentlyDeleteProject(item.id, item.lifecycleRevision ?? item.revision, confirmed);
        if (!isCurrent(operation)) return;
        if (project.id === item.id) startBlank();
      }
      if (isCurrent(operation)) await directory.refresh();
    } catch (error) {
      if (isCurrent(operation)) directory.setError(messageFrom(error));
    }
  };
  const mutate = async (item: ProjectListItem, action: LifecycleAction) => {
    const scope = stageForPage(activePage);
    if (action === "archive" && item.id === project.id && scope && hasDraft(project, scope)) { setPendingArchive(item); return; }
    await perform(item, action);
  };
  const resolvePendingArchive = async (action: "save" | "discard" | "cancel") => {
    const item = pendingArchive;
    if (!item || action === "cancel") { setPendingArchive(undefined); return; }
    const scope = stageForPage(activePage);
    if (scope && action === "save") {
      const draft = currentDraft.current;
      if (!draft || draft.scope !== scope) { setPendingArchive(undefined); return; }
      if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await commitStage(scope, draft.payload);
      if (currentDraft.current) return;
    }
    if (scope) { discardDraft(project, scope); currentDraft.current = undefined; }
    setPendingArchive(undefined);
    await perform(item, "archive");
  };
  return { pendingArchive, mutate, resolvePendingArchive };
}
