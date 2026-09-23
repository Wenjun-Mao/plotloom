import { useEffect, useRef, useState } from "react";
import type {
  ApprovalDecision,
  SamePersonComparison,
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
import { VideoPilotPanel } from "../../video-pilot";
import { useAssetKeyframeActions } from "./assets/useAssetKeyframeActions";
import { useImageJobActions } from "./image-jobs/useImageJobActions";
import { useCharacterReferenceActions } from "./references/useCharacterReferenceActions";
import { useMediaSelectionContext } from "./keyframes/useMediaSelectionContext";
import { ShotPreparationSummary } from "./ShotPreparationSummary";
import { useMediaWorkbenchData } from "./useMediaWorkbenchData";
import type { ProjectDraftQuiescence } from "../authoring/projectDraftQuiescence";

export function ManagedMediaWorkbench({
  projectId,
  storyboard,
  bible,
  graph,
  sceneBeats,
  routeId,
  selectedShot,
  storyboardRevision,
  storyBibleRevision,
  mediaDraftsEnabled,
  draftQuiescence,
  review,
  readOnly,
  onSelectShot,
  onReview,
  onReturnToBridge,
  draftChanged = false,
}: {
  projectId?: string;
  storyboard: Storyboard;
  bible: StoryBible;
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  routeId?: string;
  selectedShot: Shot | undefined;
  storyboardRevision?: number;
  storyBibleRevision?: number;
  mediaDraftsEnabled: boolean;
  draftQuiescence?: ProjectDraftQuiescence;
  review: StoryboardReview | null | undefined;
  readOnly: boolean;
  onSelectShot?: (id: string) => void;
  onReview?: () => void;
  onReturnToBridge?: () => void;
  draftChanged?: boolean;
}) {
  const currentApproval: ApprovalDecision | undefined = review?.activeApproval ?? undefined;
  const {
    workbench, setWorkbench, imageJobs, characterProposals, imageExchangeConfigured,
    previewId, setPreviewId, refresh, mediaReadPhase,
  } = useMediaWorkbenchData({
    projectId, approvalId: currentApproval?.id,
    approvalRevision: currentApproval?.subjectRevision, storyboardRevision,
    shotId: selectedShot?.id,
  });
  const mediaOwnerReadOnly = readOnly || mediaReadPhase !== "ready";
  // Durable media drafts share this read's project/approval context. A failed
  // refresh must suspend their autosave and quiescence writers too.
  const mediaDraftsReady = mediaDraftsEnabled && mediaReadPhase === "ready";
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
  const [compatibility, setCompatibility] = useState("");
  const [referenceCharacterId, setReferenceCharacterId] = useState("");
  const [referencePrimaryAssetId, setReferencePrimaryAssetId] = useState("");
  const [referenceComplementaryAssetIds, setReferenceComplementaryAssetIds] =
    useState<string[]>([]);
  const [referenceReviewer, setReferenceReviewer] = useState("creator");
  const [referenceNotes, setReferenceNotes] = useState("");
  const [proposalCharacterId, setProposalCharacterId] = useState("");
  const [proposalDirection, setProposalDirection] = useState("");
  const [proposalParentCandidateAssetId, setProposalParentCandidateAssetId] =
    useState("");
  const [samePersonReviewer, setSamePersonReviewer] = useState("creator");
  const [samePersonNotes, setSamePersonNotes] = useState("");
  const [samePersonComparisons, setSamePersonComparisons] = useState<
    SamePersonComparison[]
  >([]);
  const [previewLength, setPreviewLength] = useState(3);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const preparationDetails = useRef<HTMLDetailsElement>(null);
  const keyframeDetails = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const openDeepLink = () => {
      const targetId = window.location.hash.slice(1);
      if (targetId === "shot-character-references" && preparationDetails.current) preparationDetails.current.open = true;
      if (targetId === "shot-keyframe-review" && keyframeDetails.current) keyframeDetails.current.open = true;
      if (["shot-workbench", "shot-original", "shot-segment", "shot-story-preview", "shot-character-references", "shot-keyframe-review"].includes(targetId)) {
        requestAnimationFrame(() => document.getElementById(targetId)?.scrollIntoView({ block: "start" }));
      }
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
    draftQuiescence,
    currentApproval,
    workbench,
    imageJobs,
    imageExchangeConfigured,
    imageJobTarget,
    keptAssetId,
    previewLength,
    previewId,
    playing,
    frameIndex,
    referenceCharacterId,
    proposalCharacterId,
    setPreviewLength,
    setReferenceCharacterId,
    setProposalCharacterId,
    setSamePersonComparisons,
    setKeptAssetId,
    setFrameIndex,
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
    setWorkbench,
    previewShotIds,
    missingPreviewShotIds,
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
    prepareCharacterReferenceProposal,
    sendCharacterReferenceProposal,
    refreshCharacterReferenceProposal,
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
    proposalCharacterId,
    castRevision: undefined,
    proposalDirection,
    proposalParentCandidateAssetId,
    setProposalDirection,
    setProposalParentCandidateAssetId,
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
    >
      <div className="section-title">
        <span>Shot media workbench</span>
        <strong>镜头媒体工作台</strong>
      </div>
      <div className="button-row">
        <Field label="当前媒体镜头">
          <select
            value={selectedShot?.id ?? ""}
            onChange={(event) => onSelectShot?.(event.target.value)}
            disabled={!storyboard.shots.length}
          >
            {!selectedShot && <option value="">{storyboard.shots.length ? "未打开镜头 · 请明确选择" : "尚无镜头"}</option>}
            {storyboard.shots.map((shot) => (
              <option key={shot.id} value={shot.id}>
                {shot.title} · {shot.id}
              </option>
            ))}
          </select>
        </Field>
        <Button variant="quiet" onClick={onReview}>
          {currentApproval ? "查看分镜批准" : "前往分镜审核"}
        </Button>
      </div>
      {selectedShot && (
        <small>
          当前镜头：{selectedShot.action} · {selectedShot.durationUnits}ms
        </small>
      )}
      {error && (
        <div className="notice warning" role="alert">
          {error}
        </div>
      )}
      <div className="shot-workbench-focus">
        <div className="shot-workbench-heading"><div><small>{selectedShot ? `当前镜头 · ${selectedShot.durationUnits / 1000} 秒` : "尚未选择媒体镜头"}</small><strong>{selectedShot?.title || "请选择镜头"}</strong>{selectedShot && <p>{selectedShot.action}</p>}</div>
          <nav aria-label="镜头工作流"><a href="#shot-original">原片</a><a href="#shot-segment">调整片段</a><a href="#shot-story-preview">预览</a><a href="#shot-story-preview">用于故事</a></nav></div>
        <VideoPilotPanel projectId={projectId} shot={selectedShot} approvalId={review?.activeApproval?.id}
          storyboardRevision={storyboardRevision} selectionRevision={workbench.selectionRevision}
          keyframe={selectedBinding ? assetById.get(selectedBinding.assetId) : undefined}
          storyboard={storyboard} sceneBeats={sceneBeats} graph={graph} routeId={routeId} readOnly={mediaOwnerReadOnly} />
      </div>
      <details className="workbench-support" ref={preparationDetails}><summary>准备与参考 · 图片、角色、导入</summary>
      {selectedShot && <ShotPreparationSummary projectId={projectId} shot={selectedShot} storyboardRevision={storyboardRevision} draftChanged={draftChanged} review={review} workbench={workbench} mediaReadPhase={mediaReadPhase} onRetryMedia={() => void refresh().catch(() => undefined)} onReview={onReview} onReturnToBridge={onReturnToBridge} />}
      <div id="shot-character-references"><CharacterReferencesPanel
        projectId={projectId}
        bible={bible}
        storyBibleRevision={storyBibleRevision}
        workbench={workbench}
        proposals={characterProposals}
        assetById={assetById}
        referenceStateByCharacter={referenceStateByCharacter}
        currentReferenceByCharacter={currentReferenceByCharacter}
        form={{
          characterId: referenceCharacterId,
          primaryAssetId: referencePrimaryAssetId,
          complementaryAssetIds: referenceComplementaryAssetIds,
          reviewer: referenceReviewer,
          notes: referenceNotes,
          proposalCharacterId,
          proposalDirection,
          proposalParentCandidateAssetId,
          setCharacterId: setReferenceCharacterId,
          setPrimaryAssetId: setReferencePrimaryAssetId,
          setComplementaryAssetIds: setReferenceComplementaryAssetIds,
          setReviewer: setReferenceReviewer,
          setNotes: setReferenceNotes,
          setProposalCharacterId,
          setProposalDirection,
          setProposalParentCandidateAssetId,
        }}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        onSelectReference={() => void selectCharacterReference()}
        onRevokeReference={(characterId) => void revokeCharacterReference(characterId)}
        onPrepareProposal={() => void prepareCharacterReferenceProposal()}
        onSendProposal={(proposalId) => void sendCharacterReferenceProposal(proposalId)}
        onRefreshProposal={(proposalId) =>
          void refreshCharacterReferenceProposal(proposalId)
        }
      /></div>
      <ImageJobPanel
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
        imageJobRefreshNotice={imageJobRefreshNotice}
        selectedBinding={selectedBinding}
        onPrepare={() => void prepareImageJob()}
        onCopy={(jobId) => void copyImageJob(jobId)}
        onRefresh={(jobId) => void refreshImageJob(jobId)}
        onCancel={(jobId) => void cancelImageJob(jobId)}
      />
      <AssetImportPanel
        projectId={projectId}
        assets={workbench.assets}
        origin={origin}
        declaredAdditions={declaredAdditions}
        candidates={candidates}
        keptAssetId={keptAssetId}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        onOrigin={setOrigin}
        onDeclaredAdditions={setDeclaredAdditions}
        onImport={(file) => void importFile(file)}
        onChooseCandidate={chooseCandidate}
        onKeepCandidate={keepCandidate}
        onClear={() => {
          setCandidates([]);
          setKeptAssetId("");
        }}
      />
      {selectedBinding && (
        <small data-testid="current-reviewed-keyframe">
          当前 Shot 已保存资产 {selectedBinding.assetId.slice(0, 8)} · intent r
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
        setReviewer={setSamePersonReviewer}
        setNotes={setSamePersonNotes}
        setComparisons={setSamePersonComparisons}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        onRecord={() => void recordSamePersonReview()}
      />
      </details>
      <details className="workbench-support" ref={keyframeDetails}><summary>关键帧与静帧预览</summary>
      <div id="shot-keyframe-review"><KeyframeAndPreviewPanel
        projectId={projectId}
        workbench={workbench}
        selectedShot={selectedShot}
        selectedBinding={selectedBinding}
        keptAssetId={keptAssetId}
        retainedIdentityMapping={retainedIdentityMapping}
        assetById={assetById}
        intentEditor={intentEditor}
        activeIntent={activeIntent}
        compatibility={compatibility}
        setCompatibility={setCompatibility}
        readOnly={mediaOwnerReadOnly}
        busy={busy}
        mediaDraftsEnabled={mediaDraftsReady}
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
