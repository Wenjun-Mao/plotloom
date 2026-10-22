import { useState, type Dispatch, type SetStateAction } from "react";
import { ApiError, plotloomApi } from "../../api";
import type { useConfirmation } from "../../confirmation";
import { discardProjectDraftCaches } from "../../features/authoring/projectDraftCache";
import type { useProjectLifecycle, LifecycleTarget } from "./useProjectLifecycle";
import type { PendingProjectDeletion } from "./PendingProjectDeletions";
import type { PriorAbandonmentCandidate } from "./PriorProjectAbandonments";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";

type DeletionPreview = Awaited<ReturnType<typeof plotloomApi.deletionPreview>>;
export type DeletionFeedback = { id: string; title: string; location: "directory" | "prior" | "pending"; message: string; error: boolean };
type Options = Pick<Parameters<typeof useProjectLifecycle>[0],
  "session" | "mediaDraftQuiescence" | "reviewDraftStore" | "directory" | "startBlank"> & {
  runCommand: (item: Pick<LifecycleTarget, "id" | "brief">, action: "delete" | "abandon_delete" | "prepare_delete", execute: () => Promise<void>) => Promise<void>;
  confirmation: ReturnType<typeof useConfirmation>;
  isBusy: () => boolean;
  setClosingProjectId: Dispatch<SetStateAction<string | undefined>>;
  setCloseNotice: Dispatch<SetStateAction<string>>;
};
const deletionMessage = (error: unknown) => error instanceof Error ? error.message : "未知错误";

/** One destructive consent flow; mutation is never inferred from a refused request. */
export function useProjectDeletion({ session, mediaDraftQuiescence, reviewDraftStore, directory, startBlank,
  runCommand, confirmation, isBusy, setClosingProjectId, setCloseNotice }: Options) {
  const [deletingProjectId, setDeletingProjectId] = useState<string>();
  const [feedback, setFeedback] = useState<DeletionFeedback>();
  const performDelete = async (item: LifecycleTarget, abandonment?: Parameters<typeof plotloomApi.abandonAndDeleteProject>[1], prepared?: DeletionPreview, location: DeletionFeedback["location"] = "directory") => {
    await runCommand(item, "delete", async () => {
      const operation = session.capture();
      directory.setError("");
      setFeedback({ id: item.id, title: item.brief.title, location, message: "正在准备删除…", error: false });
      let cancelled = false;
      let erased = false;
      let attempt: ReturnType<ProjectDraftQuiescence["beginClose"]> | undefined;
      let reads: ReturnType<typeof plotloomApi.suspendProjectReads> | undefined;
      setClosingProjectId(item.id); setDeletingProjectId(item.id); setCloseNotice("");
      try {
        attempt = mediaDraftQuiescence.beginClose(item.id);
        reads = plotloomApi.suspendProjectReads(item.id);
        // Failed admission must keep unsent input. Do not drain new typing or
        // discard anything until the owning server confirms whole-home erasure.
        await attempt.suspendWrites();
        if (!await reads.settle()) throw new Error("项目读取尚未确认完成；删除未执行，请等待读取结束后重试。");
        if (!session.isCurrent(operation)) { setFeedback(undefined); return; }
        try {
          if (prepared?.mode === "stop") {
            setFeedback({ id: item.id, title: item.brief.title, location, message: "正在撤回自动派发并请求安全停止…", error: false });
            const stopped = await plotloomApi.stopForDeletion(item.id, prepared);
            if (stopped.runId !== prepared.run?.id || stopped.state !== "cancelled") throw new Error("未确认精确自动任务已停止。");
            cancelled = true;
            setFeedback({ id: item.id, title: item.brief.title, location, message: "自动运行已取消后续派发，正在核对本地任务结束与删除条件…", error: false });
            const fresh = stopped.deletionPreview;
            if (!fresh) throw new Error(stopped.blocker || "删除条件未能重新确认，请重新核对项目。");
            if (fresh.scopeHash !== prepared.scopeHash || fresh.confirmationTitle !== prepared.confirmationTitle
              || fresh.expectedProjectRevision !== prepared.expectedProjectRevision
              || fresh.expectedLifecycleRevision !== prepared.expectedLifecycleRevision
              || !["ordinary", "abandon"].includes(fresh.mode)) {
              throw new Error(fresh.blockers.join("；") || "项目内容或任务范围已改变，请重新核对删除。");
            }
            abandonment = fresh.mode === "abandon" ? { ...fresh, previewHash: fresh.previewHash! } : undefined;
          }
          setFeedback({ id: item.id, title: item.brief.title, location, message: "正在永久删除项目…", error: false });
          if (abandonment) await plotloomApi.abandonAndDeleteProject(item.id, abandonment);
          else await plotloomApi.permanentlyDeleteProject(item.id, item.lifecycleRevision ?? item.revision, item.revision, item.brief.title, prepared?.scopeHash);
          erased = true;
        }
        finally { reads.resume(); }
        let cleanupError: unknown;
        try {
          try { await attempt.discardUnsent(); }
          finally {
            try { discardProjectDraftCaches(item.id); }
            finally { reviewDraftStore.eraseProject(item.id); }
          }
        } catch (error) { cleanupError = error; }
        if (session.isCurrent(operation) && session.project.id === item.id) startBlank();
        await directory.refresh();
        setFeedback(undefined);
        setCloseNotice(cleanupError ? "项目已永久删除，但本标签页的草稿缓存未能完全清除。请关闭此标签页，不要恢复该项目的旧草稿。" : "项目已永久删除；其他项目、外部原文件和恢复快照未删除。");
      } catch (error) {
        const rejected = error instanceof ApiError && [404, 409, 422].includes(error.status);
        const phase = erased ? "项目已永久删除，但目录读取失败。" : cancelled ? "自动运行已取消后续派发，但项目未确认删除。" : prepared?.mode === "stop" ? "停止或删除结果未确认；请先检查项目任务状态。" : rejected ? "无法删除：" : "删除结果未确认，请检查项目目录后再操作：";
        setFeedback({ id: item.id, title: item.brief.title, location, message: phase + deletionMessage(error), error: true });
        // A failed destructive command may still have committed its revocation
        // and deletion intent. Refresh observation only; preserve the error and
        // every unsent draft, and never repeat the command here.
        if (abandonment && !erased) {
          try { await directory.refresh(); }
          catch { setFeedback({ id: item.id, title: item.brief.title, location, message: phase + deletionMessage(error) + " 项目目录重新读取也未完成，请稍后检查。", error: true }); }
        }
      } finally {
        try { reads?.resume(); }
        finally {
          try { attempt?.finish(); }
          finally { setClosingProjectId(undefined); setDeletingProjectId(undefined); }
        }
      }
    });
  };
  const requestDeletion = async (item: LifecycleTarget) => {
    if (isBusy() || (session.project.id && mediaDraftQuiescence.isClosing(session.project.id))) return;
    await runCommand(item, "prepare_delete", async () => {
      const operation = session.capture();
      setFeedback(current => current?.error ? current : { id: item.id, title: item.brief.title, location: "directory", message: "正在核对删除条件…", error: false });
      try {
        const preview = await plotloomApi.deletionPreview(item.id);
        if (!session.isCurrent(operation)) { setFeedback(current => current?.error ? current : undefined); return; }
        if (preview.mode === "blocked") {
          setFeedback({ id: item.id, title: item.brief.title, location: "directory", message: preview.blockers.join("；"), error: true });
          return;
        }
        setFeedback(current => current?.error ? current : undefined);
        const stop = preview.mode === "stop";
        const abandon = preview.mode === "abandon";
        const target = { id: item.id, brief: { title: preview.confirmationTitle },
          revision: preview.expectedProjectRevision, lifecycleRevision: preview.expectedLifecycleRevision };
        confirmation.requestConfirmation({
          title: stop ? "停止任务并删除项目" : "永久删除项目",
          message: stop ? "取消此项目后续自动派发，并请求原任务安全停止；核对本地任务结束后永久删除故事内容、草稿和所有素材，无法撤销。"
            : "永久删除该项目的故事内容、草稿、图片、视频和任务记录，无法撤销。",
          details: `${preview.confirmationTitle}\n项目版本 r${preview.expectedProjectRevision} · 生命周期 r${preview.expectedLifecycleRevision}\n${preview.run ? `自动任务：${preview.run.state}（${preview.run.id}）\n` : ""}仍未确认远程结果的任务：${preview.unknownAttemptIds.join("、") || "无"}\n${preview.stopWarnings?.length ? `将请求精确取消；以下占用若未结束，项目仍会保留：\n${preview.stopWarnings.join("\n")}\n` : ""}其他项目、账号设置、外部原文件和恢复快照保留。`,
          challenge: { expected: preview.confirmationTitle, label: "输入完整片名以确认删除", hint: `请原样输入：${preview.confirmationTitle}` },
          ...((stop || abandon) ? { acknowledgement: "我理解停止与删除不会证明远程任务取消、成功或未执行；原始未知结果与占用证据继续保留。" } : {}),
          action: () => performDelete(target, abandon ? { ...preview, previewHash: preview.previewHash! } : undefined, preview),
        });
      } catch (error) {
        if (session.isCurrent(operation)) setFeedback({ id: item.id, title: item.brief.title, location: "directory", message: deletionMessage(error), error: true });
      }
    });
  };
  const requestAbandonment = async (item: LifecycleTarget) => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    if (isBusy()) return;
    await runCommand(item, "abandon_delete", async () => {
      const operation = session.capture();
      setFeedback({ id: item.id, title: item.brief.title, location: "prior", message: "正在核对删除条件…", error: false });
      try {
        const preview = await plotloomApi.abandonmentPreview(item.id);
        if (!session.isCurrent(operation)) { setFeedback(current => current?.error ? current : undefined); return; }
        if (!preview.eligible) { setFeedback({ id: item.id, title: item.brief.title, location: "prior", message: preview.blockers.join("；"), error: true }); return; }
        const consent = { expectedProjectRevision: preview.expectedProjectRevision,
          expectedLifecycleRevision: preview.expectedLifecycleRevision,
          confirmationTitle: preview.confirmationTitle, previewHash: preview.previewHash, scopeHash: preview.scopeHash };
        setFeedback(current => current?.error ? current : undefined);
        confirmation.requestConfirmation({ title: "放弃任务并永久删除项目",
          message: "撤销此项目的自动派发和交付发布权限，然后永久删除项目及所有素材，无法撤销。",
          details: `${preview.confirmationTitle}\n项目版本 r${preview.expectedProjectRevision} · 生命周期 r${preview.expectedLifecycleRevision}\n仍未确认远程结果的任务：${preview.unknownAttemptIds.join("、") || "无"}\n其他项目、账号设置、外部原文件和恢复快照保留。主机上的原始不确定结果与占用证据仍保留。`,
          acknowledgement: "我理解远程任务可能仍已执行或继续执行；删除不会证明其取消、成功或释放占用。",
          challenge: { expected: preview.confirmationTitle, label: "输入完整片名以确认放弃和删除", hint: `请原样输入：${preview.confirmationTitle}` },
          action: () => performDelete({ id: item.id, brief: { title: preview.confirmationTitle },
            revision: preview.expectedProjectRevision, lifecycleRevision: preview.expectedLifecycleRevision }, consent, undefined, "prior"),
        });
      } catch (error) { if (session.isCurrent(operation)) setFeedback({ id: item.id, title: item.brief.title, location: "prior", message: deletionMessage(error), error: true }); }
    });
  };
  const abandonPrior = (candidate: PriorAbandonmentCandidate) => requestAbandonment({ id: candidate.projectId,
    brief: { title: candidate.title }, revision: candidate.projectRevision, lifecycleRevision: candidate.lifecycleRevision });
  const retryDeletion = async (pending: PendingProjectDeletion) => {
    await runCommand({ id: pending.projectId, brief: { title: pending.confirmationTitle } }, "abandon_delete", async () => {
      const operation = session.capture();
      setFeedback(current => current?.error ? current : { id: pending.projectId, title: pending.confirmationTitle, location: "pending", message: "正在核对原删除请求…", error: false });
      try {
        const preview = pending.revoked ? pending : await plotloomApi.abandonmentPreview(pending.projectId);
        if (!session.isCurrent(operation)) { setFeedback(current => current?.error ? current : undefined); return; }
        if ("eligible" in preview && !preview.eligible) { setFeedback({ id: pending.projectId, title: pending.confirmationTitle, location: "pending", message: preview.blockers.join("；"), error: true }); return; }
        const consent = { expectedLifecycleRevision: preview.expectedLifecycleRevision,
          expectedProjectRevision: preview.expectedProjectRevision, confirmationTitle: preview.confirmationTitle,
          previewHash: preview.previewHash, scopeHash: preview.scopeHash };
        setFeedback(current => current?.error ? current : undefined);
        confirmation.requestConfirmation({ title: "重试永久删除项目", message: "继续明确确认的项目删除请求。远程未知结果与原始占用证据继续保留。",
          details: `${preview.confirmationTitle}\n${pending.revoked ? "主机派发与发布权限已撤销；只继续删除原目录。" : "已重新核对当前服务器预览；确认后撤销原任务发布权限，再删除。"}${"unknownAttemptIds" in preview ? `\n仍未确认远程结果的任务：${preview.unknownAttemptIds.join("、") || "无"}` : ""}`,
          challenge: { expected: preview.confirmationTitle, label: "输入完整片名以确认重试删除", hint: `请原样输入：${preview.confirmationTitle}` },
          acknowledgement: "我理解此操作无法撤销，也不证明远程任务已取消或未执行。",
          action: () => performDelete({ id: pending.projectId, brief: { title: preview.confirmationTitle },
            revision: preview.expectedProjectRevision, lifecycleRevision: preview.expectedLifecycleRevision }, consent, undefined, "pending"),
        });
      } catch (error) { if (session.isCurrent(operation)) setFeedback({ id: pending.projectId, title: pending.confirmationTitle, location: "pending", message: deletionMessage(error), error: true }); }
    });
  };
  return { requestDeletion, abandonPrior, retryDeletion, deletingProjectId, deletionFeedback: feedback };
}
