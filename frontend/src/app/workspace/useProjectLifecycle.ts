import { useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { discardDraft, hasDraft, type DraftScope } from "../../draft-registry";
import { messageFrom, stageForPage } from "./contracts";
import type { ProjectListItem, ServerStageName, WorkspaceProject } from "../../types";
import type { WorkspaceSession } from "./useWorkspaceSession";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";

type LifecycleAction = "archive" | "restore" | "duplicate" | "delete" | "close" | "open";
type LifecycleSession = Pick<WorkspaceSession, "project" | "activePage" | "capture" | "isCurrent" | "acceptCanonicalProject">;

/** Owns directory lifecycle commands and the archive-after-draft decision. */
export function useProjectLifecycle({
  session,
  currentDraft,
  commitProject,
  commitStage,
  mediaDraftQuiescence,
  directory,
  openProject,
  startBlank,
  explicitProjectClose,
}: {
  session: LifecycleSession;
  currentDraft: React.MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
  commitProject: (patch: Partial<WorkspaceProject>) => Promise<void>;
  commitStage: <T>(stage: ServerStageName, content: T) => Promise<void>;
  mediaDraftQuiescence: ProjectDraftQuiescence;
  directory: { close: () => void; refresh: () => Promise<void>; setError: (error: string) => void };
  openProject: (projectId: string) => void;
  startBlank: () => void;
  explicitProjectClose: boolean;
}) {
  const duplicateKeys = useRef(new Map<string, string>());
  const [pendingArchive, setPendingArchive] = useState<{ item: ProjectListItem; action: "archive" | "close" } | undefined>();
  const perform = async (item: ProjectListItem, action: LifecycleAction) => {
    const operation = session.capture();
    try {
      if (action === "close" || action === "open") {
        if (!explicitProjectClose) return;
        if (action === "close") {
          const attempt = mediaDraftQuiescence.beginClose(item.id);
          if (!await attempt.drain() || !attempt.canCommit()) {
            throw new Error("媒体草稿未保存；项目仍保持打开状态。");
          }
          try {
            // `canCommit` runs in this continuation, before yielding to fetch;
            // a writer registered by a late edit therefore aborts Close rather
            // than being stranded behind a closed project.
            if (!attempt.canCommit()) throw new Error("项目草稿仍在更新；请重试关闭。");
            await plotloomApi.closeProject(item.id);
          } finally {
            attempt.finish();
          }
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
    }
  };
  const mutate = async (item: ProjectListItem, action: LifecycleAction) => {
    const scope = stageForPage(session.activePage);
    if ((action === "archive" || action === "close") && item.id === session.project.id && scope && hasDraft(session.project, scope)) { setPendingArchive({ item, action }); return; }
    await perform(item, action);
  };
  const resolvePendingArchive = async (action: "save" | "discard" | "cancel") => {
    const pending = pendingArchive;
    if (!pending || action === "cancel") { setPendingArchive(undefined); return; }
    const scope = stageForPage(session.activePage);
    if (scope && action === "save" && pending.action === "close") {
      if (!await mediaDraftQuiescence.flush(pending.item.id)) return;
    } else if (scope && action === "save") {
      const draft = currentDraft.current;
      if (!draft || draft.scope !== scope) { setPendingArchive(undefined); return; }
      if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await commitStage(scope, draft.payload);
      if (currentDraft.current) return;
    }
    // Close keeps the current ref through the server-draft receipt and the
    // following admission transition. Clearing it before Close completes lets
    // the generic recovery effect paint a just-acknowledged draft over the
    // closed view. `startBlank` owns the final workflow cleanup instead.
    if (scope && pending.action !== "close") {
      discardDraft(session.project, scope);
      currentDraft.current = undefined;
    }
    setPendingArchive(undefined);
    await perform(pending.item, pending.action);
  };
  return { pendingArchive, mutate, resolvePendingArchive };
}
