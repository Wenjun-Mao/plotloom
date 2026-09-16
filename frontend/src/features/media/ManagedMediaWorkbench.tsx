import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ApprovalDecision,
  CharacterReferenceProposal,
  ImageJob,
  SamePersonComparison,
  SceneBeatPlan,
  Shot,
  StoryBible,
  StoryGraph,
  Storyboard,
  StoryboardReview,
  VisualWorkbench,
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
import { useAssetKeyframeActions } from "./assets/useAssetKeyframeActions";
import { useImageJobActions } from "./image-jobs/useImageJobActions";
import { useCharacterReferenceActions } from "./references/useCharacterReferenceActions";
import { useMediaSelectionContext } from "./keyframes/useMediaSelectionContext";
import type { ProjectDraftQuiescence } from "../authoring/projectDraftQuiescence";

function previewKey(projectId: string): string {
  return `plotloom:still-preview:${projectId}`;
}
const emptyWorkbench: VisualWorkbench = {
  assets: [],
  selectionRevision: 0,
  visualIntents: [],
  reviewedKeyframes: [],
  characterReferences: { states: [], decisions: [] },
  samePersonReviews: { revision: 0, reviews: [] },
  previews: [],
};

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
}) {
  const [workbench, setWorkbench] = useState<VisualWorkbench>(emptyWorkbench);
  const [imageJobs, setImageJobs] = useState<ImageJob[]>([]);
  const [characterProposals, setCharacterProposals] = useState<
    CharacterReferenceProposal[]
  >([]);
  const [imageExchangeConfigured, setImageExchangeConfigured] = useState(false);
  const [copiedAssignment, setCopiedAssignment] = useState("");
  const [copiedAssignmentStatus, setCopiedAssignmentStatus] = useState<
    "copied" | "manual" | ""
  >("");
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
  const [previewId, setPreviewId] = useState("");
  const [playing, setPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const requestSequence = useRef(0);
  const copiedAssignmentRef = useRef<HTMLTextAreaElement>(null);
  const currentApproval: ApprovalDecision | undefined =
    review?.activeApproval ?? undefined;

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!projectId) return;
      const sequence = ++requestSequence.current;
      const [next, jobs, proposals] = await Promise.all([
        plotloomApi.getVisualWorkbench(projectId, signal),
        plotloomApi.getImageJobs(projectId, signal),
        plotloomApi.getCharacterReferenceProposals(projectId, signal),
      ]);
      if (signal?.aborted || sequence !== requestSequence.current) return;
      setWorkbench(next);
      setImageJobs(jobs.jobs);
      setCharacterProposals(proposals.proposals);
      setImageExchangeConfigured(jobs.configured);
      const saved = window.localStorage.getItem(previewKey(projectId));
      const preferred =
        next.previews.find((item) => item.id === saved) ?? next.previews[0];
      setPreviewId(preferred?.id ?? "");
    },
    [projectId],
  );

  // Approval and authored-board changes determine preview applicability.  An
  // aborted or superseded request may never repaint a newer approval context.
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch((loadError) => {
      if (!controller.signal.aborted)
        setError(
          loadError instanceof Error ? loadError.message : "无法读取导入媒体",
        );
    });
    return () => controller.abort();
  }, [
    refresh,
    currentApproval?.id,
    currentApproval?.subjectRevision,
    storyboardRevision,
    selectedShot?.id,
  ]);

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
    mediaDraftsEnabled,
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
    mediaDraftsEnabled,
    imageJobContextId,
    setBusy,
    setError,
    setCopiedAssignment,
    setCopiedAssignmentStatus,
    setImageJobRefreshNotice,
    setImageJobTarget,
    setKeptAssetId,
    setCandidates,
    refresh,
  });
  const {
    selectCharacterReference,
    revokeCharacterReference,
    prepareCharacterReferenceProposal,
    copyCharacterReferenceProposal,
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
    storyBibleRevision,
    proposalDirection,
    proposalParentCandidateAssetId,
    setProposalDirection,
    setProposalParentCandidateAssetId,
    setCopiedAssignment,
    setCopiedAssignmentStatus,
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
      className="managed-media-workbench"
      data-testid="managed-media-workbench"
    >
      <div className="section-title">
        <span>Imported stills · P0</span>
        <strong>非生成式审核关键帧</strong>
      </div>
      <p className="muted">
        原始字节、来源声明、可审核意图和精确批准绑定都会保留。P0
        导入不生成媒体；P1 image jobs 通过受限的手动 Codex 交接单独运行。
      </p>
      <div className="button-row">
        <Field label="当前媒体镜头">
          <select
            value={selectedShot?.id ?? ""}
            onChange={(event) => onSelectShot?.(event.target.value)}
            disabled={!storyboard.shots.length}
          >
            {!storyboard.shots.length && <option value="">尚无镜头</option>}
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
      <CharacterReferencesPanel
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
        readOnly={readOnly}
        busy={busy}
        onSelectReference={() => void selectCharacterReference()}
        onRevokeReference={(characterId) => void revokeCharacterReference(characterId)}
        onPrepareProposal={() => void prepareCharacterReferenceProposal()}
        onCopyProposal={(proposalId) => void copyCharacterReferenceProposal(proposalId)}
        onRefreshProposal={(proposalId) =>
          void refreshCharacterReferenceProposal(proposalId)
        }
      />
      <ImageJobPanel
        imageExchangeConfigured={imageExchangeConfigured}
        prerequisite={imageJobPrerequisite}
        target={imageJobTarget}
        setTarget={setImageJobTarget}
        eligibleRefinementCandidates={eligibleRefinementCandidates}
        direction={imageJobDirection}
        mediaDraftsEnabled={mediaDraftsEnabled}
        readOnly={readOnly}
        busy={busy}
        copiedAssignment={copiedAssignment}
        copiedAssignmentStatus={copiedAssignmentStatus}
        copiedAssignmentRef={copiedAssignmentRef}
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
        readOnly={readOnly}
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
        readOnly={readOnly}
        busy={busy}
        onRecord={() => void recordSamePersonReview()}
      />
      <KeyframeAndPreviewPanel
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
        readOnly={readOnly}
        busy={busy}
        mediaDraftsEnabled={mediaDraftsEnabled}
        review={review}
        storyboardRevision={storyboardRevision}
        storyboard={storyboard}
        sceneBeats={sceneBeats}
        graph={graph}
        routeId={routeId}
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
      />
    </Panel>
  );
}
