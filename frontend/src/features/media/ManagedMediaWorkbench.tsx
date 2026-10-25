import { useReviewEditorDraft } from "../authoring/ReviewDraftContext";
import { useEffect, useState } from "react";
import type {
  ApprovalDecision,
  SceneBeatPlan,
  Shot,
  StoryBible,
  StoryGraph,
  Storyboard,
  StoryboardReview,
} from "../../types";
import { plotloomApi } from "../../api";
import { Button, Field, Panel } from "../../components";
import {
  type ImageJobDraftTarget,
} from "../../visual-intent-drafts";
import { CharacterReferencesPanel } from "./references/CharacterReferencesPanel";
import { ImageJobPanel } from "./image-jobs/ImageJobPanel";
import { AssetImportPanel } from "./assets/AssetImportPanel";
import { SamePersonReviewPanel } from "./references/SamePersonReviewPanel";
import { KeyframeAndPreviewPanel } from "./keyframes/KeyframeAndPreviewPanel";
import { ShotPresentationReview } from "./keyframes/ShotPresentationReview";
import { generatedCandidateState } from "./keyframes/shot-presentation";
import { shotLabel } from "../../shot-label";
import { VideoPilotPanel } from "../../video-pilot";
import { hasCurrentStoryboardApproval } from "./current-storyboard-approval";
import { useAssetKeyframeActions } from "./assets/useAssetKeyframeActions";
import { useImageJobActions } from "./image-jobs/useImageJobActions";
import { useCharacterReferenceActions } from "./references/useCharacterReferenceActions";
import { useMediaSelectionContext } from "./keyframes/useMediaSelectionContext";
import { ownsOrdinaryIntent } from "./keyframes/visual-intent-ownership";
import { useKeyframeCompatibilityDraft } from "./keyframes/useKeyframeCompatibilityDraft";
import { ShotPreparationSummary } from "./ShotPreparationSummary";
import { revealMediaOwner } from "./media-owner-navigation";
import { useMediaWorkbenchData } from "./useMediaWorkbenchData";
import type { ProjectDraftQuiescence } from "../authoring/projectDraftQuiescence";
import type { SamePersonComparisonDraft } from "../../same-person-review-types";

export function ManagedMediaWorkbench({
  projectId,
  videoReadVersion,
  lifecycleRevision,
  projectRevision,
  lifecycleStatus,
  storyboard,
  bible,
  graph,
  sceneBeats,
  routeId,
  selectedShot,
  storyboardRevision,
  mediaDraftsEnabled,
  draftQuiescence,
  review,
  readOnly,
  onSelectShot,
  onReview,
  onEditShot,
  onReturnToBridge,
  draftChanged = false,
}: {
  projectId?: string;
  videoReadVersion?: number;
  lifecycleRevision?: number;
  projectRevision?: number;
  lifecycleStatus?: "active" | "archived";
  storyboard: Storyboard;
  bible: StoryBible;
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  routeId?: string;
  selectedShot: Shot | undefined;
  storyboardRevision?: number;
  mediaDraftsEnabled: boolean;
  draftQuiescence?: ProjectDraftQuiescence;
  review: StoryboardReview | null | undefined;
  readOnly: boolean;
  onSelectShot?: (id: string) => void;
  onReview?: () => void;
  onEditShot?: () => void;
  onReturnToBridge?: () => void;
  draftChanged?: boolean;
}) {
  const currentApproval: ApprovalDecision | undefined = review?.activeApproval ?? undefined;
  const approvalCurrent = hasCurrentStoryboardApproval(review, storyboardRevision, draftChanged);
  const {
    workbench, acknowledgeSelectionRevision, refreshAfterProjectWrite, imageJobs, imageExchangeConfigured,
    previewId, setPreviewId, refresh, mediaReadPhase,
  } = useMediaWorkbenchData({
    projectId, projectRevision, lifecycleRevision, approvalId: currentApproval?.id,
    approvalRevision: currentApproval?.subjectRevision, storyboardRevision,
    shotId: selectedShot?.id,
  });
  const mediaOwnerReadOnly = readOnly || mediaReadPhase !== "ready";
  // Read readiness does not grant archived authoring permission. Keep local
  // buffers mounted while suspending autosave and quiescence writers.
  const mediaDraftsReady = mediaDraftsEnabled && lifecycleStatus !== "archived"
    && mediaReadPhase === "ready";
  const [imageJobTarget, setImageJobTarget] = useState<ImageJobDraftTarget>({
    kind: "original",
  });
  const [imageJobRefreshNotice, setImageJobRefreshNotice] = useState<
    Record<string, string>
  >({});
  const [candidates, setCandidates] = useState<string[]>([]);
  const [keptAssetId, setKeptAssetId] = useState("");
  const [origin, setOrigin] = useState("Local creator import");
  const [declaredAdditions, setDeclaredAdditions] = useState("reference only");
  const [referenceCharacterId, setReferenceCharacterId] = useState("");
  const [referencePrimaryAssetId, setReferencePrimaryAssetId] = useState("");
  const [referenceComplementaryAssetIds, setReferenceComplementaryAssetIds] =
    useState<string[]>([]);
  const [referenceReviewer, setReferenceReviewer] = useState("creator");
  const [referenceNotes, setReferenceNotes] = useState("");
  const [samePersonReviewer, setSamePersonReviewer] = useState("creator");
  const [samePersonNotes, setSamePersonNotes] = useState("");
  const [samePersonComparisons, setSamePersonComparisons] = useState<
    SamePersonComparisonDraft[]
  >([]);
  const referenceWorking = useReviewEditorDraft(projectId || "", "managed_reference", `storyboard:${storyboardRevision ?? 0}`, text => {
    const input = JSON.parse(text) as { notes: string };
    if (typeof input.notes !== "string") throw new Error("角色参考审阅文字无法读取。");
    setReferenceNotes(input.notes);
  }, mediaOwnerReadOnly, undefined, referenceCharacterId);
  const importWorking = useReviewEditorDraft(projectId || "", "managed_reference", `storyboard:${storyboardRevision ?? 0}`, text => {
    const input = JSON.parse(text) as { origin: string; declaredAdditions: string };
    if (typeof input.origin !== "string" || typeof input.declaredAdditions !== "string") throw new Error("导入来源说明无法读取。");
    setOrigin(input.origin); setDeclaredAdditions(input.declaredAdditions);
  }, mediaOwnerReadOnly, undefined, `import-${selectedShot?.id || "root"}`);
  const [previewLength, setPreviewLength] = useState(3);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [presentationReview, setPresentationReview] = useState<{ shotId: string; revision: number }>();
  const [playing, setPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  useEffect(() => {
    const openDeepLink = () => {
      revealMediaOwner(window.location.hash.slice(1), "auto");
    };
    openDeepLink();
    window.addEventListener("hashchange", openDeepLink);
    return () => window.removeEventListener("hashchange", openDeepLink);
  }, [selectedShot?.id]);

  const {
    maxPreviewLength,
    previewShotIds,
    preview,
    missingPreviewShotIds,
    selectedBinding,
    assetById,
    referenceStateByCharacter,
    currentReferenceByCharacter,
    selectedIdentityMapping,
    retainedIdentityMapping,
    currentReviewByBinding,
    identityReviewMissingShotIds,
    activeIntent,
    intentEditor,
    intentDraft,
    retainCrossShotFrame,
    eligibleRefinementCandidates,
    targetCandidate,
    imageJobContextId,
    imageJobDirection,
    imageJobPrerequisite,
  } = useMediaSelectionContext({
    projectId,
    storyboard,
    bible,
    selectedShot,
    storyboardRevision,
    mediaDraftsEnabled: mediaDraftsReady,
    editingDisabled: mediaOwnerReadOnly || busy,
    draftQuiescence,
    currentApproval,
    workbench,
    mediaReadPhase,
    imageJobs,
    imageExchangeConfigured,
    imageJobTarget,
    keptAssetId,
    previewLength,
    previewId,
    playing,
    frameIndex,
    referenceCharacterId,
    setPreviewLength,
    setReferenceCharacterId,
    setSamePersonComparisons,
    setKeptAssetId,
    setFrameIndex,
  });
  const samePersonWorking = useReviewEditorDraft(projectId || "", "same_person", `binding:${storyboardRevision ?? 0}:${selectedBinding?.id ?? ""}:${JSON.stringify(selectedIdentityMapping)}`, text => {
    const input = JSON.parse(text) as { notes: string; comparisons: Array<{ characterId: string; identityNotes: string; stateNotes: string; uncertaintyReason?: string }> };
    if (typeof input.notes !== "string" || !Array.isArray(input.comparisons)) throw new Error("身份审阅文字无法读取。");
    setSamePersonNotes(input.notes);
    setSamePersonComparisons(current => current.map(item => {
      const authored = input.comparisons.find(value => value.characterId === item.characterId);
      return authored ? { ...item, identityNotes: authored.identityNotes, stateNotes: authored.stateNotes, uncertaintyReason: authored.uncertaintyReason } : item;
    }));
  }, mediaOwnerReadOnly, undefined, selectedBinding?.id || selectedShot?.id || "");
  const rememberIdentityNotes = (comparisons: SamePersonComparisonDraft[], notes = samePersonNotes) => {
    samePersonWorking.changed(JSON.stringify({ notes, comparisons: comparisons.map(({ characterId, identityNotes, stateNotes, uncertaintyReason }) => ({ characterId, identityNotes, stateNotes, uncertaintyReason })) }));
  };
  const { compatibility, setCompatibility, notice: compatibilityNotice, stale: compatibilityStale } = useKeyframeCompatibilityDraft({
    projectId, shot: selectedShot, assetId: keptAssetId, approval: currentApproval,
    storyboardRevision, intent: activeIntent, asset: assetById.get(keptAssetId), mediaReadPhase, readOnly: mediaOwnerReadOnly || busy,
  });
  const {
    chooseCandidate,
    keepCandidate,
    selectPreview,
    importFile,
    saveIntent,
    selectKeyframe,
    createPreview,
  } = useAssetKeyframeActions({
    projectId,
    origin,
    declaredAdditions,
    setBusy,
    setError,
    refresh,
    refreshAfterProjectWrite,
    setCandidates,
    setKeptAssetId,
    setPreviewId,
    setFrameIndex,
    setPlaying,
    mediaDraftsEnabled: mediaDraftsReady,
    selectedShot,
    intentEditor,
    intentDraft,
    keptAssetId,
    currentApproval,
    storyboardRevision,
    activeIntent,
    compatibility,
    workbench,
    acknowledgeSelectionRevision,
    previewShotIds,
    missingPreviewShotIds,
    presentationRevision: presentationReview?.shotId === selectedShot?.id ? presentationReview?.revision : 0,
  });
  const {
    prepareImageJob,
    copyImageJob,
    refreshImageJob,
    cancelImageJob,
  } = useImageJobActions({
    projectId,
    selectedShot,
    currentApproval,
    storyboardRevision,
    imageJobTarget,
    targetCandidate,
    selectedBinding,
    imageJobDirection,
    mediaDraftsEnabled: mediaDraftsReady,
    imageJobContextId,
    setBusy,
    setError,
    setImageJobRefreshNotice,
    setImageJobTarget,
    setKeptAssetId,
    setCandidates,
    refresh,
  });
  // Existing refresh validates immutable package/currentness before it may
  // publish a candidate. Observe only current exported jobs automatically.
  useEffect(() => {
    if (!projectId || mediaReadPhase !== "ready") return;
    const timer = window.setInterval(() => {
      const outstanding = imageJobs.filter(
        (job) => job.current && job.state === "exported" && !job.deliveries.some(
          (delivery) => delivery.diagnosticCode === "package_conflict",
        ),
      );
      void Promise.all(outstanding.map((job) => plotloomApi.refreshImageJob(projectId, job.id)))
        .then((results) => results.some((result) => result.state !== "awaiting_delivery") ? refresh() : undefined)
        // A rejection is durable server state. Reload it before the next tick
        // so a package conflict stops observation, while a normal partial
        // delivery remains eligible for its next automatic check.
        .catch(() => refresh().catch(() => undefined));
    }, 3_000);
    return () => window.clearInterval(timer);
  }, [imageJobs, projectId, refresh, mediaReadPhase]);
  const {
    selectCharacterReference,
    revokeCharacterReference,
    recordSamePersonReview,
  } = useCharacterReferenceActions({
    projectId,
    referenceCharacterId,
    referencePrimaryAssetId,
    referenceComplementaryAssetIds,
    referenceReviewer,
    referenceNotes,
    referenceStateByCharacter,
    setBusy,
    setError,
    setReferenceNotes,
    setReferenceComplementaryAssetIds,
    refresh,
    selectedBinding,
    selectedIdentityMapping,
    samePersonReviewer,
    samePersonNotes,
    samePersonComparisons,
    workbench,
    setSamePersonNotes,
  });
  return (
    <Panel
      id="shot-workbench"
      className="managed-media-workbench"
      data-testid="managed-media-workbench"
    >{intentEditor.retainedNotice}{imageJobDirection.retainedNotice}{referenceWorking.notice}{samePersonWorking.notice}{importWorking.notice}{compatibilityNotice}
      <div className="section-title">
        <span>为当前镜头制作并审核图片和视频</span>
        <strong>镜头媒体工作台</strong>
      </div>
      {projectId && selectedShot && mediaDraftsEnabled && <ShotPresentationReview
        key={`${projectId}:${selectedShot.id}`} projectId={projectId} shotId={selectedShot.id}
        approval={currentApproval} storyboardRevision={storyboardRevision} readOnly={mediaOwnerReadOnly || busy}
        onLoaded={revision => setPresentationReview({ shotId: selectedShot.id, revision })} onSaved={refresh} quiescence={draftQuiescence}
      />}
      <div className="button-row">
        <Field label="当前镜头">
          <select
            value={selectedShot?.id ?? ""}
            onChange={(event) => onSelectShot?.(event.target.value)}
            disabled={!storyboard.shots.length}
          >
            {!selectedShot && <option value="">{storyboard.shots.length ? "未打开镜头 · 请明确选择" : "尚无镜头"}</option>}
            {storyboard.shots.map((shot) => (
              <option key={shot.id} value={shot.id}>
                {shotLabel(shot)} · {shot.id}
              </option>
            ))}
          </select>
        </Field>
        <Button variant="quiet" onClick={onReview}>
          {approvalCurrent ? "查看分镜批准" : "前往分镜审核"}
        </Button>
        <Button variant="quiet" disabled={!selectedShot} onClick={onEditShot}>编辑镜头细节</Button>
      </div>
      {selectedShot && (
        <small>
          镜头动作：{selectedShot.action} · {selectedShot.durationUnits}ms
        </small>
      )}
      {error && (
        <div className="notice warning" role="alert">
          {error}
        </div>
      )}
      <div className="shot-workbench-focus">
        <div className="shot-workbench-heading"><div><small>{selectedShot ? `当前镜头 · ${selectedShot.durationUnits / 1000} 秒` : "尚未选择镜头"}</small><strong>{selectedShot ? shotLabel(selectedShot) : "请选择镜头"}</strong>{selectedShot && <p>{selectedShot.action}</p>}</div></div>
        <VideoPilotPanel videoReadVersion={videoReadVersion} projectId={projectId} projectRevision={projectRevision} lifecycleRevision={lifecycleRevision} lifecycleStatus={lifecycleStatus} shot={selectedShot} approvalId={review?.activeApproval?.id} approvalCurrent={approvalCurrent}
          storyboardRevision={storyboardRevision} selectionRevision={workbench.selectionRevision}
          keyframe={selectedBinding ? assetById.get(selectedBinding.assetId) : undefined}
          reviewedBinding={selectedBinding} samePersonReviewId={selectedBinding ? currentReviewByBinding.get(selectedBinding.id)?.id : undefined}
          mediaReadPhase={mediaReadPhase}
          storyboard={storyboard} sceneBeats={sceneBeats} graph={graph} routeId={routeId} readOnly={mediaOwnerReadOnly} />
      </div>
      <details className="workbench-support"><summary>准备与参考 · 图片、角色、导入</summary>
      {selectedShot && <ShotPreparationSummary projectId={projectId} shot={selectedShot} storyboardRevision={storyboardRevision} draftChanged={draftChanged} review={review} workbench={workbench} mediaReadPhase={mediaReadPhase} onRetryMedia={() => void refresh().catch(() => undefined)} onReview={onReview} onReturnToBridge={onReturnToBridge} />}
      <div id="shot-character-references"><CharacterReferencesPanel
        projectId={projectId}
        bible={bible}
        workbench={workbench}
        assetById={assetById}
        referenceStateByCharacter={referenceStateByCharacter}
        currentReferenceByCharacter={currentReferenceByCharacter}
        form={{
          characterId: referenceCharacterId,
          primaryAssetId: referencePrimaryAssetId,
          complementaryAssetIds: referenceComplementaryAssetIds,
          reviewer: referenceReviewer,
          notes: referenceNotes,
          setCharacterId: setReferenceCharacterId,
          setPrimaryAssetId: setReferencePrimaryAssetId,
          setComplementaryAssetIds: setReferenceComplementaryAssetIds,
          setReviewer: setReferenceReviewer,
          setNotes: value => { setReferenceNotes(value); referenceWorking.changed(JSON.stringify({ notes: value })); },
        }}
        readOnly={mediaOwnerReadOnly || referenceWorking.stale}
        mediaReadPhase={mediaReadPhase}
        busy={busy}
        onSelectReference={() => void selectCharacterReference()}
        onRevokeReference={(characterId) => void revokeCharacterReference(characterId)}
      /></div>
      <ImageJobPanel
        reviewedKeyframes={workbench.reviewedKeyframes}
        imageExchangeConfigured={imageExchangeConfigured}
        prerequisite={imageJobPrerequisite}
        target={imageJobTarget}
        setTarget={setImageJobTarget}
        eligibleRefinementCandidates={eligibleRefinementCandidates}
        direction={imageJobDirection}
        mediaDraftsEnabled={mediaDraftsReady}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        imageJobs={imageJobs}
        shotId={selectedShot?.id}
        mediaReadPhase={mediaReadPhase}
        imageJobRefreshNotice={imageJobRefreshNotice}
        selectedBinding={selectedBinding}
        onPrepare={() => void prepareImageJob()}
        onCopy={(jobId) => void copyImageJob(jobId)}
        onRefresh={(jobId) => void refreshImageJob(jobId)}
        onCancel={(jobId) => void cancelImageJob(jobId)}
      />
      <AssetImportPanel
        onReuseFrame={retainCrossShotFrame}
        reviewedKeyframes={workbench.reviewedKeyframes}
        projectId={projectId}
        shotId={selectedShot?.id}
        assets={workbench.assets}
        origin={origin}
        declaredAdditions={declaredAdditions}
        candidates={candidates}
        keptAssetId={keptAssetId}
        readOnly={mediaOwnerReadOnly || importWorking.stale}
        busy={busy}
        onOrigin={value => { setOrigin(value); importWorking.changed(JSON.stringify({ origin: value, declaredAdditions })); }}
        onDeclaredAdditions={value => { setDeclaredAdditions(value); importWorking.changed(JSON.stringify({ origin, declaredAdditions: value })); }}
        onImport={(file) => void importFile(file)}
        onChooseCandidate={chooseCandidate}
        onKeepCandidate={(assetId) => {
          const targetUse = workbench.visualIntents.some((intent) => intent.assetId === assetId && intent.intent.targetUse?.targetShotId === selectedShot?.id);
          const source = workbench.reviewedKeyframes.find((binding) => binding.assetId === assetId && binding.shotId !== selectedShot?.id);
          const ordinaryOwned = workbench.visualIntents.some((intent) => intent.assetId === assetId && ownsOrdinaryIntent(intent, selectedShot?.id, workbench.reviewedKeyframes));
          if (source && !targetUse && !ordinaryOwned) retainCrossShotFrame(source); else keepCandidate(assetId);
        }}
        onClear={() => {
          setCandidates([]);
          setKeptAssetId("");
        }}
      />
      {selectedBinding && (
        <small data-testid="current-reviewed-keyframe">
          当前镜头已保存图片 {selectedBinding.assetId.slice(0, 8)} · 画面意图 r
          {selectedBinding.visualIntentRevision ?? "—"}
        </small>
      )}
      <SamePersonReviewPanel
        projectId={projectId}
        selectedBinding={selectedBinding}
        selectedIdentityMapping={selectedIdentityMapping}
        assetById={assetById}
        currentReviewByBinding={currentReviewByBinding}
        workbench={workbench}
        reviewer={samePersonReviewer}
        notes={samePersonNotes}
        comparisons={samePersonComparisons}
        setReviewer={value => { const next = typeof value === "function" ? value(samePersonReviewer) : value; setSamePersonReviewer(next); }}
        setNotes={value => { const next = typeof value === "function" ? value(samePersonNotes) : value; setSamePersonNotes(next); rememberIdentityNotes(samePersonComparisons, next); }}
        setComparisons={update => setSamePersonComparisons(current => { const next = typeof update === "function" ? update(current) : update; rememberIdentityNotes(next); return next; })}
        readOnly={mediaOwnerReadOnly || samePersonWorking.stale}
        busy={busy}
        onRecord={() => void recordSamePersonReview()}
      />
      </details>
      <details className="workbench-support"><summary>关键帧与静帧预览</summary>
      <div id="shot-keyframe-review"><KeyframeAndPreviewPanel
        projectId={projectId}
        workbench={workbench}
        selectedShot={selectedShot}
        selectedBinding={selectedBinding}
        keptAssetId={keptAssetId}
        retainedIdentityMapping={retainedIdentityMapping}
        candidateState={generatedCandidateState(keptAssetId, imageJobs)}
        assetById={assetById}
        intentEditor={intentEditor}
        activeIntent={activeIntent}
        compatibility={compatibility}
        compatibilityStale={compatibilityStale}
        setCompatibility={setCompatibility}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        mediaDraftsEnabled={mediaDraftsReady}
        mediaReadPhase={mediaReadPhase}
        review={review}
        maxPreviewLength={maxPreviewLength}
        previewLength={previewLength}
        setPreviewLength={setPreviewLength}
        previewShotIds={previewShotIds}
        missingPreviewShotIds={missingPreviewShotIds}
        identityReviewMissingShotIds={identityReviewMissingShotIds}
        preview={preview}
        previewId={previewId}
        frameIndex={frameIndex}
        setFrameIndex={setFrameIndex}
        playing={playing}
        setPlaying={setPlaying}
        onSaveIntent={() => void saveIntent()}
        onSelectKeyframe={() => void selectKeyframe()}
        onCreatePreview={() => void createPreview()}
        onSelectPreview={selectPreview}
      /></div>
      </details>
    </Panel>
  );
}
