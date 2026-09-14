import type { Dispatch, SetStateAction } from "react";
import type {
  ApprovalDecision,
  Shot,
  VisualIntent,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";
import { useVisualIntentDraft } from "../../../visual-intent-drafts";

type IntentEditor = ReturnType<typeof useVisualIntentDraft>;

function previewKey(projectId: string): string {
  return `plotloom:still-preview:${projectId}`;
}

export function useAssetKeyframeActions({
  projectId,
  origin,
  declaredAdditions,
  setBusy,
  setError,
  refresh,
  setCandidates,
  setKeptAssetId,
  setPreviewId,
  setFrameIndex,
  setPlaying,
  mediaDraftsEnabled,
  selectedShot,
  intentEditor,
  intentDraft,
  keptAssetId,
  currentApproval,
  storyboardRevision,
  activeIntent,
  compatibility,
  workbench,
  setWorkbench,
  previewShotIds,
  missingPreviewShotIds,
}: {
  projectId?: string;
  origin: string;
  declaredAdditions: string;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string>>;
  refresh: (signal?: AbortSignal) => Promise<void>;
  setCandidates: Dispatch<SetStateAction<string[]>>;
  setKeptAssetId: Dispatch<SetStateAction<string>>;
  setPreviewId: Dispatch<SetStateAction<string>>;
  setFrameIndex: Dispatch<SetStateAction<number>>;
  setPlaying: Dispatch<SetStateAction<boolean>>;
  mediaDraftsEnabled: boolean;
  selectedShot: Shot | undefined;
  intentEditor: IntentEditor;
  intentDraft: IntentEditor["value"];
  keptAssetId: string;
  currentApproval: ApprovalDecision | undefined;
  storyboardRevision?: number;
  activeIntent: VisualIntent | undefined;
  compatibility: string;
  workbench: VisualWorkbench;
  setWorkbench: Dispatch<SetStateAction<VisualWorkbench>>;
  previewShotIds: string[];
  missingPreviewShotIds: string[];
}) {
  const chooseCandidate = (id: string) =>
    setCandidates((current) =>
      current.includes(id)
        ? current.filter((candidate) => candidate !== id)
        : [...current.slice(-1), id],
    );
  const keepCandidate = (id: string) => {
    setKeptAssetId(id);
    setCandidates((current) =>
      current.includes(id) ? current : [...current.slice(-1), id],
    );
  };
  const selectPreview = (id: string) => {
    setPreviewId(id);
    setFrameIndex(0);
    setPlaying(false);
    if (projectId) window.localStorage.setItem(previewKey(projectId), id);
  };
  const importFile = async (file: File | undefined) => {
    if (!projectId || !file) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.importManagedAsset(projectId, file, {
        origin,
        rights: "unknown",
        declaredAdditions: declaredAdditions
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      await refresh();
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "导入失败");
    } finally {
      setBusy(false);
    }
  };
  const saveIntent = async () => {
    if (!projectId || !keptAssetId || (mediaDraftsEnabled && !selectedShot)) return;
    if (intentEditor.stale) {
      setError("已保存意图已有新版本；草稿仍保留，请先检查并重新载入。");
      return;
    }
    const sourceRefs = intentDraft.sourceRefs
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    if (!sourceRefs.length) {
      setError("先记录至少一个来源引用，再保存可审核意图。");
      return;
    }
    if (
      mediaDraftsEnabled
      && (!intentEditor.serverReady || intentEditor.serverRevision < 1 || intentEditor.serverConflict)
    ) {
      setError("等待当前视觉意图草稿得到项目 CAS 确认后再保存。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await plotloomApi.createVisualIntent(projectId, keptAssetId, {
        role: "shot_keyframe",
        identityIntent: intentDraft.identityIntent || undefined,
        compositionIntent: intentDraft.compositionIntent || undefined,
        styleIntent: intentDraft.styleIntent || undefined,
        sourceRefs,
        ...(mediaDraftsEnabled ? {
          shotId: selectedShot!.id,
          consumedDraft: {
            editorScope: "visual_intent" as const,
            entityId: `${selectedShot!.id}:${keptAssetId}`,
            draftRevision: intentEditor.serverRevision,
          },
        } : {}),
      });
      await refresh();
      await intentEditor.clear();
    } catch (intentError) {
      setError(
        intentError instanceof Error ? intentError.message : "意图保存失败",
      );
    } finally {
      setBusy(false);
    }
  };
  const selectKeyframe = async () => {
    if (
      !projectId ||
      !keptAssetId ||
      !selectedShot ||
      !currentApproval ||
      !storyboardRevision ||
      !activeIntent
    )
      return;
    if (intentEditor.dirty) {
      setError("先保存或放弃意图草稿，再审核选择。");
      return;
    }
    if (!compatibility.trim()) {
      setError("请记录此关键帧与已批准镜头的兼容性说明。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const selected = await plotloomApi.selectReviewedKeyframe(projectId, {
        assetId: keptAssetId,
        shotId: selectedShot.id,
        sceneId: selectedShot.sceneId,
        expectedSelectionRevision: workbench.selectionRevision,
        storyboardRevision,
        approvalId: currentApproval.id,
        compatibilityNote: compatibility.trim(),
        visualIntentId: activeIntent.id,
        visualIntentRevision: activeIntent.revision,
      });
      // A shot change can supersede the read refresh that follows a successful
      // selection. The mutation response is the authoritative revision, so
      // advance the local concurrency token before enabling the next shot.
      // The full refresh below still owns bindings, intents, and preview state.
      setWorkbench((current) => ({
        ...current,
        selectionRevision: Math.max(
          current.selectionRevision,
          selected.selectionRevision,
        ),
      }));
      await refresh();
    } catch (selectionError) {
      setError(
        selectionError instanceof Error ? selectionError.message : "选择失败",
      );
    } finally {
      setBusy(false);
    }
  };
  const createPreview = async () => {
    if (
      !projectId ||
      !selectedShot ||
      !currentApproval ||
      !storyboardRevision ||
      !previewShotIds.length
    )
      return;
    if (missingPreviewShotIds.length) {
      setError(`先为 ${missingPreviewShotIds.join("、")} 完成审核关键帧选择。`);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await plotloomApi.createStillPreview(projectId, {
        sceneId: selectedShot.sceneId,
        shotIds: previewShotIds,
        expectedSelectionRevision: workbench.selectionRevision,
        storyboardRevision,
        approvalId: currentApproval.id,
      });
      await refresh();
      selectPreview(created.id);
    } catch (previewError) {
      setError(
        previewError instanceof Error ? previewError.message : "预览创建失败",
      );
    } finally {
      setBusy(false);
    }
  };

  return {
    chooseCandidate,
    keepCandidate,
    selectPreview,
    importFile,
    saveIntent,
    selectKeyframe,
    createPreview,
  };
}
