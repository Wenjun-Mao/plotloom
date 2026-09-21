import type { Dispatch, SetStateAction } from "react";
import type {
  ApprovalDecision,
  ReviewedKeyframe,
  Shot,
  VideoBackendProfile,
} from "../../../types";
import { plotloomApi } from "../../../api";
import {
  type ImageJobDraftTarget,
  useImageJobDirectionDraft,
} from "../../../visual-intent-drafts";

type ImageJobDirection = ReturnType<typeof useImageJobDirectionDraft>;

export function useImageJobActions({
  projectId,
  selectedShot,
  currentApproval,
  storyboardRevision,
  imageJobTarget,
  targetCandidate,
  selectedBinding,
  imageJobDirection,
  mediaDraftsEnabled,
  imageJobContextId,
  setBusy,
  setError,
  setImageJobRefreshNotice,
  setImageJobTarget,
  setKeptAssetId,
  setCandidates,
  refresh,
}: {
  projectId?: string;
  selectedShot: Shot | undefined;
  currentApproval: ApprovalDecision | undefined;
  storyboardRevision?: number;
  imageJobTarget: ImageJobDraftTarget;
  targetCandidate: { assetId: string } | undefined;
  selectedBinding: ReviewedKeyframe | undefined;
  imageJobDirection: ImageJobDirection;
  mediaDraftsEnabled: boolean;
  imageJobContextId: string;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string>>;
  setImageJobRefreshNotice: Dispatch<SetStateAction<Record<string, string>>>;
  setImageJobTarget: Dispatch<SetStateAction<ImageJobDraftTarget>>;
  setKeptAssetId: Dispatch<SetStateAction<string>>;
  setCandidates: Dispatch<SetStateAction<string[]>>;
  refresh: (signal?: AbortSignal) => Promise<void>;
}) {
  const prepareImageJob = async () => {
    if (!projectId || !selectedShot || !currentApproval || !storyboardRevision)
      return;
    if (imageJobTarget.kind === "refinement" && !targetCandidate) {
      setError("参考细化只能使用当前镜头已审核选择的当前 P1 候选。");
      return;
    }
    if (imageJobTarget.kind === "keyframe_adaptation" && !selectedBinding) {
      setError("关键帧比例适配需要当前镜头的审核关键帧。");
      return;
    }
    if (imageJobDirection.stale) {
      setError(
        "这个方向草稿来自旧的 Approval、分镜或参考上下文；请显式恢复或放弃它。",
      );
      return;
    }
    if (!imageJobDirection.value.trim()) {
      setError("请先说明这次原始图或参考细化要冻结的画面呈现变化。");
      return;
    }
    if (
      mediaDraftsEnabled
      && (!imageJobDirection.serverReady || imageJobDirection.serverRevision < 1 || imageJobDirection.serverConflict)
    ) {
      setError("等待当前 image 方向草稿得到项目 CAS 确认后再准备 job。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await plotloomApi.prepareImageJob(projectId, {
        approvalId: currentApproval.id,
        shotId: selectedShot.id,
        storyboardRevision,
        parentCandidateAssetId:
          imageJobTarget.kind === "refinement"
            ? imageJobTarget.parentCandidateAssetId
            : undefined,
        keyframeAdaptationProfileId:
          imageJobTarget.kind === "keyframe_adaptation"
            ? imageJobTarget.profileId
            : undefined,
        presentationChange: imageJobDirection.value.trim(),
        contractVersion: 3,
        ...(mediaDraftsEnabled ? {
          contextId: imageJobContextId,
          consumedDraft: {
            editorScope: "image_direction" as const,
            entityId: `${selectedShot.id}:${imageJobDirection.targetId}`,
            draftRevision: imageJobDirection.serverRevision,
          },
        } : {}),
      });
      // The prepare request consumed this exact durable direction atomically.
      await imageJobDirection.clearConsumed();
      await refresh();
    } catch (jobError) {
      setError(
        jobError instanceof Error ? jobError.message : "无法准备 image job",
      );
    } finally {
      setBusy(false);
    }
  };
  const requestKeyframeAdaptation = (profile: VideoBackendProfile) => {
    setImageJobTarget({
      kind: "keyframe_adaptation",
      profileId: profile.id,
      profileLabel: profile.label,
    });
    setError("");
  };
  const acceptPreparedCrop = async (assetId: string) => {
    setKeptAssetId(assetId);
    setCandidates((current) => current.includes(assetId) ? current : [...current.slice(-1), assetId]);
    await refresh();
  };
  const copyImageJob = async (jobId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const copied = await plotloomApi.copyImageJob(projectId, jobId);
      setImageJobRefreshNotice((current) => ({
        ...current,
        [jobId]: "已发送给专用 specialist；队列接受不代表生成或 delivery。完成后将自动检查 receipt。",
      }));
      await refresh();
    } catch (jobError) {
      setError(
        jobError instanceof Error
          ? jobError.message
          : "无法发送 specialist image job",
      );
    } finally {
      setBusy(false);
    }
  };
  const refreshImageJob = async (jobId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const result = await plotloomApi.refreshImageJob(projectId, jobId);
      setImageJobRefreshNotice((current) => ({
        ...current,
        [jobId]:
          result.state === "awaiting_delivery"
            ? "尚未收到 delivery。specialist 完成 JPEG/PNG 与 completion.json 后再检查；这不是失败或已选择。"
            : "已检查 delivery receipt。",
      }));
      await refresh();
    } catch (jobError) {
      setError(
        jobError instanceof Error
          ? jobError.message
          : "无法刷新 specialist delivery",
      );
    } finally {
      setBusy(false);
    }
  };
  const cancelImageJob = async (jobId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.cancelImageJob(
        projectId,
        jobId,
        "creator cancelled manual image job",
      );
      await refresh();
    } catch (jobError) {
      setError(
        jobError instanceof Error ? jobError.message : "无法取消 image job",
      );
    } finally {
      setBusy(false);
    }
  };

  return {
    prepareImageJob,
    requestKeyframeAdaptation,
    acceptPreparedCrop,
    copyImageJob,
    refreshImageJob,
    cancelImageJob,
  };
}
