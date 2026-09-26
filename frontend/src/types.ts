export type StageName = "project_brief" | "story_bible" | "story_graph" | "scene_beats" | "storyboard";
export type ServerStageName = Exclude<StageName, "project_brief">;
export type RunStatus = "queued" | "running" | "succeeded" | "quarantined" | "cancel_requested" | "cancelled" | "failed";
export type MediaKind = "image" | "video";

/** Stable server-side authoring failure projected back to one editor field. */
export interface ValidationIssue {
  code: string;
  path: string;
  message: string;
}

export interface ProjectBrief {
  title: string;
  synopsis: string;
  genre: string | null;
  visualStyle: string | null;
  language: string;
  aspectRatio: string;
  targetPlaythroughSeconds: number;
  decisionPointsPerPath: number;
  endingCount: number;
  nodeBudget: number;
  maxOutDegree: number;
  desiredJoinCount: number;
  shotsPerSceneMin: number;
  shotsPerSceneMax: number;
  shotCountPolicy: "advisory" | "strict";
}

export interface CharacterCard {
  id: string;
  name: string;
  role: string | null;
  description: string;
  goal: string;
  traits: string[];
  visualAnchors: string[];
  soundAnchors: string[];
  voiceAnchors: string[];
  allowedStates: string[];
  continuityRules: string[];
}

export interface LocationCard {
  id: string;
  name: string;
  description: string;
  visualAnchors: string[];
  soundAnchors: string[];
  allowedStates: string[];
  continuityRules: string[];
}

export interface PropCard {
  id: string;
  name: string;
  description: string;
  visualAnchors: string[];
  soundAnchors: string[];
  allowedStates: string[];
  continuityRules: string[];
}

export interface StoryBible {
  logline: string;
  premise: string;
  genre: string;
  tone: string;
  audience: string;
  narrativePromise: string;
  themes: string[];
  worldRules: string[];
  visualLanguage: string;
  knownFacts: string[];
  openQuestions: string[];
  sourceNotes: string[];
  characters: CharacterCard[];
  locations: LocationCard[];
  props: PropCard[];
}

export interface StoryNode {
  id: string;
  title: string;
  kind: "start" | "decision" | "scene" | "join" | "ending";
  summary: string;
}

export interface StoryEdge {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  kind: "choice" | "continuation";
  choiceText: string | null;
  stateEffects: Record<string, unknown>;
  entityStateEffects: RequiredEntityState[];
}

export interface JoinContract {
  id: string;
  joinNodeId: string;
  incomingNodeIds: string[];
  requiredStateKeys: string[];
  allowedDifferences: string[];
  reconciliation: string;
  notes: string;
}

export interface StoryGraph {
  startNodeId: string;
  nodes: StoryNode[];
  edges: StoryEdge[];
  joinContracts: JoinContract[];
}

export interface ContinuityState {
  facts: Record<string, unknown>;
  screenDirection: string | null;
  lighting: string | null;
  sound: string | null;
  notes: string[];
  entityStates: RequiredEntityState[];
}

export type EntityType = "character" | "location" | "prop";
export interface RequiredEntityState {
  entityType: EntityType;
  entityId: string;
  state: string;
}

export interface DramaticScene {
  id: string;
  storyNodeId: string;
  title: string;
  objective: string;
  locationId: string | null;
  characterIds: string[];
  beatIds: string[];
  order: number;
  durationBudgetUnits: number;
  entryState: ContinuityState;
  exitState: ContinuityState;
}

export interface Beat {
  id: string;
  sceneId: string;
  order: number;
  description: string;
  purpose: string;
  visibleEvent: string;
  immediateResult: string;
  dramaticChange: string;
  entryState: ContinuityState;
  exitState: ContinuityState;
  continuityAnchors: string[];
  continuityDelta: Record<string, unknown>;
}

export interface DialogueCue {
  id: string;
  beatId: string;
  order: number;
  speakerId: string | null;
  voiceOver: string | null;
  text: string;
  language: string;
  delivery: "measured" | "natural" | "brisk";
  performanceNotes: string;
  estimatedDurationUnits: number;
}

export interface SceneBeatPlan {
  scenes: DramaticScene[];
  beats: Beat[];
  dialogueCues: DialogueCue[];
}

export interface AudioEvent {
  id: string;
  kind: "ambience" | "sound_effect" | "diegetic_sound" | "diegetic_music" | "score";
  description: string;
  startOffsetUnits: number;
  durationUnits: number;
}

export interface AudioPlan {
  events: AudioEvent[];
}

export interface Shot {
  id: string;
  sceneId: string;
  order: number;
  title: string;
  shotSize: "extreme_wide" | "wide" | "full" | "medium" | "close_up" | "extreme_close_up" | "insert";
  durationUnits: number;
  cameraAngle: string;
  cameraMovement: string;
  composition: string;
  visualIntent: string;
  motionIntent: string;
  action: string;
  transition: string;
  characterIds: string[];
  locationId: string | null;
  propIds: string[];
  cueIds: string[];
  audioPlan: AudioPlan;
  requiredEntityStates: RequiredEntityState[];
  entryState: ContinuityState;
  exitState: ContinuityState;
}

export interface Storyboard {
  shots: Shot[];
  shotBeatLinks: ShotBeatLink[];
}

export interface ShotBeatLink {
  shotId: string;
  beatId: string;
  role: "primary" | "supporting";
  coverageWeight: number;
}

export interface ManagedAsset {
  id: string;
  projectId: string;
  originalHash: string;
  displayHash: string;
  mimeType: string;
  byteSize: number;
  width: number;
  height: number;
  createdAt: string;
  provenance: { origin: string; rights: "known" | "unknown"; rightsNote: string | null; declaredAdditions: string[] } | null;
}

export interface CharacterImportedAppearance {
  id: string; projectId: string; characterId: string; assetId: string; label: string;
  characterContext: Record<string, unknown>; characterContextHash: string; current: boolean;
  createdAt: string; asset: ManagedAsset;
}

export interface StillPreviewFrame {
  shotId: string;
  assetId: string;
  displayHash: string;
  durationMs: number;
  bindingId: string;
  visualIntentId: string | null;
  visualIntentRevision: number | null;
  identityReviewId?: string;
  identityReferenceDecisionIds?: string[];
}

export interface VisualIntent {
  id: string;
  assetId: string;
  revision: number;
  intent: {
    role: "protagonist_reference" | "location_reference" | "shot_keyframe";
    identityIntent?: string | null;
    compositionIntent?: string | null;
    styleIntent?: string | null;
    sourceRefs: string[];
  };
}

export interface ReviewedKeyframe {
  id: string;
  assetId: string;
  shotId: string;
  sceneId: string;
  selectionRevision: number;
  visualIntentId: string | null;
  visualIntentRevision: number | null;
  compatibilityNote: string;
}

export interface StillPreview {
  id: string;
  manifest: {
    projectionVersion: number;
    sceneId: string;
    shotIds: string[];
    storyboardRevision: number;
    storyboardEntityRevisionId: string;
    approvalId: string;
    approvalGateSetVersion: string;
    canonicalInputRevisions: Record<string, number>;
    selectionRevision: number;
    frames: StillPreviewFrame[];
  };
  manifestHash: string;
  createdAt: string;
  state: "current" | "stale" | "revoked" | "missing" | "corrupt";
}

export interface VisualWorkbench {
  assets: ManagedAsset[];
  selectionRevision: number;
  visualIntents: VisualIntent[];
  reviewedKeyframes: ReviewedKeyframe[];
  characterReferences: CharacterReferencesResponse;
  samePersonReviews: SamePersonReviewsResponse;
  previews: StillPreview[];
}

export interface VideoPilotBudget {
  limitSeconds: number;
  reservedSeconds: number;
  remainingSeconds: number;
  attempts: Array<{ videoJobId: string; event: string; seconds: number; createdAt: string }>;
}

export interface VideoBackend {
  enabled: boolean;
  reason?: string;
  adapterId?: string;
  adapterVersion?: string;
  provider?: string;
  model?: string;
  durationSeconds?: number;
  resolution?: string;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  frameCount?: number | null;
  nativeAudio?: boolean;
  requiresAspectPolicy?: boolean;
  inputAspectPolicy?: "reject_mismatch";
  allowsLetterbox?: boolean;
  allowsCenterCrop?: boolean;
  tracksPaidWanPilot?: boolean;
  profileContractVersion?: number;
  defaultProfileId?: string;
  qualifiedDurationSeconds?: number[];
  profiles?: VideoBackendProfile[];
}

export interface VideoBackendProfile {
  id: string;
  version: number;
  label: string;
  quality?: number;
  orientation: "landscape" | "portrait";
  tier: "fast" | "standard" | "high_resolution";
  width: number;
  height: number;
  durationSeconds: number;
  fps: number;
  frameCount: number;
  nativeAudio: boolean;
}

export interface VideoJob {
  id: string;
  projectId: string;
  state: "prepared" | "dispatching" | "submitted" | "outcome_unknown" | "retrieve_needed" | "ingested" | "discard_pending" | "discarded" | "cancelled" | "failed";
  cancelRequestedAt: string | null;
  requestedSeconds: number;
  current: boolean;
  selected: boolean;
  selectionRevision: number;
  reviews: Array<{ id: string; reviewer: string; decision: "select" | "reject"; note: string; createdAt: string }>;
  providerPredictionId: string | null;
  outputHash: string | null;
  observed: {
    durationSeconds: number; width: number; height: number; videoCodec: string; audioCodec: string | null;
    frameRate?: number | null; frameCount?: number | null;
  } | null;
  segments?: VideoSegment[];
  playbackSegment?: VideoSegment | null;
  error: string | null;
  snapshot: Record<string, unknown>;
}

export interface VideoSegment {
  id: string;
  videoJobId: string;
  shotId: string;
  inFrame: number;
  outFrame: number;
  authoredDurationUnits: number;
  sourceProbe: { frameCount: number; fps: string; [key: string]: unknown };
  derivativeProbe: { frameCount: number; fps: string; [key: string]: unknown };
  derivativeHash: string;
  current: boolean;
  selected: boolean;
  selectedRevision: number | null;
  createdAt: string;
}

export interface CharacterReferenceState {
  characterId: string;
  revision: number;
  activeDecisionId: string | null;
  current: boolean;
}

export interface CharacterReferenceDecision {
  id: string;
  projectId: string;
  characterId: string;
  referenceRevision: number;
  characterContext: Record<string, unknown>;
  characterContextHash: string;
  primaryAssetId: string;
  complementaryAssetIds: string[];
  assetHashes: Array<{ assetId: string; originalHash: string }>;
  reviewer: string | null;
  notes: string | null;
  current: boolean;
  revokedAt: string | null;
  revokedBy: string | null;
  revocationReason: string | null;
  createdAt: string;
}

export interface CharacterReferencesResponse {
  states: CharacterReferenceState[];
  decisions: CharacterReferenceDecision[];
}

export interface SamePersonComparison {
  characterId: string;
  judgment: "pass" | "fail";
  identityNotes: string;
  stateNotes: string;
}

export interface SamePersonReview {
  id: string;
  projectId: string;
  bindingId: string;
  reviewRevision: number;
  referenceBindings: Array<{ characterId: string; referenceDecisionId: string; referenceRevision: number; assetHashes: string[] }>;
  comparisons: SamePersonComparison[];
  reviewer: string;
  notes: string;
  current: boolean;
  createdAt: string;
}

export interface SamePersonReviewsResponse {
  revision: number;
  reviews: SamePersonReview[];
}

export interface CharacterReferenceProposalCandidate {
  id: string;
  assetId: string;
  proposalId: string;
  outputFilename: string;
  outputHash: string;
  role: "original" | "refinement";
  asset: ManagedAsset | null;
  createdAt: string;
}

export interface CharacterReferenceProposal {
  id: string;
  projectId: string;
  characterId: string;
  parentCandidateAssetId: string | null;
  request: Record<string, unknown>;
  requestHash: string;
  state: "prepared" | "exported" | "delivered" | "cancelled";
  current: boolean;
  exportedAt: string | null;
  cancelledAt: string | null;
  cancellationReason: string | null;
  createdAt: string;
  deliveries: Array<{
    id: string;
    deliveryId: string | null;
    state: "accepted" | "inapplicable" | "rejected";
    diagnosticCode: string | null;
    publicationPhase: "final" | null;
    manifestHash: string | null;
    createdAt: string;
    candidates: CharacterReferenceProposalCandidate[];
  }>;
}

export interface CharacterReferenceProposalsResponse {
  configured: boolean;
  proposals: CharacterReferenceProposal[];
}

export interface ArtReferenceProposalCandidate {
  id: string;
  assetId: string;
  proposalId: string;
  outputFilename: string;
  outputHash: string;
  role: "art_reference";
  asset: ManagedAsset | null;
  createdAt: string;
}

export interface ArtReferenceProposal {
  id: string;
  projectId: string;
  subjectType: "scene" | "prop";
  subjectId: string;
  request: Record<string, unknown>;
  requestHash: string;
  state: "prepared" | "exported" | "delivered" | "cancelled";
  current: boolean;
  exportedAt: string | null;
  cancelledAt: string | null;
  cancellationReason: string | null;
  createdAt: string;
  deliveries: Array<{
    id: string;
    deliveryId: string | null;
    state: "accepted" | "inapplicable" | "rejected";
    diagnosticCode: string | null;
    manifestHash: string | null;
    createdAt: string;
    candidates: ArtReferenceProposalCandidate[];
  }>;
}

export interface ArtReferenceProposalsResponse {
  configured: boolean;
  proposals: ArtReferenceProposal[];
}

export interface ArtReferenceDecisionState {
  subjectType: "scene" | "prop";
  subjectId: string;
  revision: number;
  activeDecisionId: string | null;
  current: boolean;
}

export interface ArtReferenceDecision {
  id: string;
  projectId: string;
  subjectType: "scene" | "prop";
  subjectId: string;
  referenceRevision: number;
  acceptedArtRevision: number;
  acceptedArtHash: string;
  subject: Record<string, unknown>;
  subjectHash: string;
  assetId: string;
  assetHash: string;
  proposalId: string;
  candidateId: string;
  current: boolean;
  createdAt: string;
}

export interface ArtReferenceDecisionsResponse {
  states: ArtReferenceDecisionState[];
  decisions: ArtReferenceDecision[];
}

export interface ImageJobCandidate {
  id: string;
  assetId: string;
  jobId: string;
  outputFilename: string;
  outputHash: string;
  role: "original" | "refinement" | "keyframe_adaptation";
  asset: ManagedAsset | null;
  createdAt: string;
}

export interface ImageJobDelivery {
  id: string;
  deliveryId: string | null;
  state: "accepted" | "inapplicable" | "rejected";
  diagnosticCode: string | null;
  manifestHash: string | null;
  createdAt: string;
  candidates: ImageJobCandidate[];
}

export interface ImageJob {
  id: string;
  projectId: string;
  productionUnitId: string;
  parentJobId: string | null;
  parentCandidateAssetId: string | null;
  request: {
    schemaVersion?: number;
    kind: "original" | "refinement" | "keyframe_adaptation";
    visualProposal?: Record<string, unknown>;
    frozenSnapshot?: {
      visibleCharacterIds?: string[];
      characterIdentity?: Array<{
        characterId: string;
        referenceDecisionId: string;
        referenceRevision: number;
        acceptedCast?: {
          revision: number;
          contentHash: string;
          castCharacterId: string;
          appearance: string | null;
          image: unknown;
        } | null;
        assets: Array<{ assetId: string; originalHash: string }>;
      }>;
      keyframeAdaptation?: {
        sourceBindingId: string;
        sourceAssetId: string;
        targetProfile: { id: string; width: number; height: number };
      };
    };
  };
  requestHash: string;
  state: "prepared" | "exported" | "delivered" | "cancelled";
  current: boolean;
  exportedAt: string | null;
  cancelledAt: string | null;
  cancellationReason: string | null;
  createdAt: string;
  deliveries: ImageJobDelivery[];
}

export interface ImageJobsResponse {
  configured: boolean;
  jobs: ImageJob[];
}

export interface QuarantineItem {
  /** Work-unit identity, never an attempt or an artifact id. */
  id: string;
  stage: ServerStageName;
  code: string;
  message: string;
  status?: "quarantined" | "outcome_unknown" | "failed" | "cancelled";
  attempt?: RunProgressAttempt | null;
  maxAttempts?: number;
  sealed?: boolean;
  repairEligible?: boolean;
  repairReasonCode?: string | null;
  /** @deprecated Legacy trace-only evidence; never populated from progress. */
  rawOutput?: string;
  /** @deprecated Legacy trace-only hint; exact repair accepts no client guidance. */
  repairHint?: string;
}

export interface WorkspaceProject {
  id?: string;
  /**
   * A local workspace needs an owner that is distinct from every other
   * unsaved workspace. It deliberately never crosses the API boundary.
   */
  clientDraftOwner?: string;
  /**
   * Local creation provenance for a teaching workspace. When set, its first
   * save atomically installs the canonical prefix through this stage. This
   * never crosses the API boundary or survives canonical hydration.
   */
  initialStageOnFirstSave?: ServerStageName;
  revision: number;
  updatedAt?: string;
  archivedAt?: string | null;
  lifecycleRevision?: number;
  lifecycleStatus?: "active" | "archived";
  brief: ProjectBrief;
  storyBible: StoryBible;
  storyGraph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  storyboard: Storyboard;
  quarantines: QuarantineItem[];
  staleStages: ServerStageName[];
  stageRevisions: Record<ServerStageName, number>;
}

export interface ProjectResource {
  id: string;
  revision: number;
  brief: ProjectBrief;
  createdAt: string;
  updatedAt: string;
  /** Archived projects stay addressable but are read-only in the workbench. */
  archivedAt: string | null;
  lifecycleRevision: number;
  lifecycleStatus: "active" | "archived";
}

/** One bounded server-acknowledged editor draft in project.sqlite3. */
export type AuthoringDraftScope = "brief" | ServerStageName | "visual_intent" | "image_direction";
export interface AuthoringDraft {
  projectId: string;
  editorScope: AuthoringDraftScope;
  entityId: string;
  baseCanonicalRevision: number;
  draftRevision: number;
  payload: Record<string, unknown>;
  updatedAt: string;
}

export interface CanonicalDraftConsumption {
  editorScope: AuthoringDraftScope;
  entityId: string;
  draftRevision: number;
}

export interface LatestRunSummary {
  id: string;
  kind: PipelineRun["kind"];
  status: RunStatus;
  requestedStages: ServerStageName[];
  createdAt: string;
  finishedAt: string | null;
}

export interface ProjectListItem extends ProjectResource {
  /** Present only when the selected backend supports explicit folder close. */
  operationalState?: "open" | "closed" | null;
  stageStatuses: Record<ServerStageName, StageHead["status"]>;
  latestRun: LatestRunSummary | null;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
  nextCursor: string | null;
}

export interface ProjectDuplicateResponse {
  project: ProjectCreationResponse;
  copiedThrough: ServerStageName | null;
  omittedStages: ServerStageName[];
}

/** A server-owned portable recovery copy; browser callers never choose its path. */
export interface ProjectSnapshotFile {
  relativePath: string;
  contentHash: string;
  sizeBytes: number;
}

export interface ProjectSnapshotManifest {
  snapshotFormatVersion: number;
  snapshotId: string;
  projectId: string;
  createdAt: string;
  databaseHash: string;
  files: ProjectSnapshotFile[];
}

export interface ProjectSnapshotReceipt {
  operationId: string;
  snapshotId: string;
  projectId: string;
  status: "complete";
  location: string;
  manifest: ProjectSnapshotManifest;
}

/** A stage payload installed atomically with a newly-created project. */
export interface InitialProjectStage {
  stage: ServerStageName;
  payload: unknown;
}

/**
 * The project-creation endpoint accepts either a brief on its own or a
 * contiguous canonical stage prefix beginning with story_bible.
 */
export interface ProjectCreationRequest {
  brief: ProjectBrief;
  initialStages?: InitialProjectStage[];
}

export interface StageHead {
  stage: ServerStageName;
  revision: number;
  status: "ready" | "stale" | "missing";
  entityRevisionId: string | null;
  contentHash: string | null;
  schemaVersion: 1 | 2;
  inputRevisions: Partial<Record<ServerStageName, number>>;
  staleReasons: string[];
  updatedAt: string;
}

export interface StageEnvelope<T = unknown> {
  head: StageHead;
  payload: T | null;
}

export interface StageEnvelopesResponse {
  stages: StageEnvelope[];
}

export interface GateEvidence {
  key: string;
  value: string;
}

export interface GateResult {
  id: string;
  gateSetVersion: string;
  gateId: string;
  evaluatedInputHash: string;
  required: boolean;
  status: "pass" | "fail" | "skipped" | "not_applicable";
  severity: "info" | "warning" | "error";
  entityPath: Array<string | number>;
  evidence: GateEvidence[];
  reason: string;
}

export interface GateEvaluation {
  gateSetVersion: string;
  evaluatedInputHash: string;
  results: GateResult[];
}

export interface ApprovalDecision {
  id: string;
  projectId: string;
  entityRevisionId: string;
  subjectType: string;
  subjectId: string;
  subjectRevision: number;
  contentHash: string;
  canonicalInputRevisions: Partial<Record<ServerStageName, number>>;
  gateSetVersion: string;
  decision: "approve" | "revoke";
  reviewer: string;
  note: string | null;
  createdAt: string;
}

export interface ApprovalClosure {
  decision: ApprovalDecision;
  active: boolean;
  staleReasons: string[];
}

export interface StoryboardReview {
  head: StageHead;
  gateEvaluation: GateEvaluation | null;
  decisions: ApprovalClosure[];
  activeApproval: ApprovalDecision | null;
}

/** The create/replay response is the complete canonical project aggregate. */
export interface ProjectCreationResponse extends ProjectResource, StageEnvelopesResponse {}

export interface TraceEvent {
  id: string;
  at: string;
  stage: ServerStageName;
  kind: "request" | "prompt" | "response" | "validation" | "candidate" | "install" | "error";
  title: string;
  status: "pending" | "ok" | "warning" | "error";
  systemPrompt?: string;
  userPrompt?: string;
  payload?: unknown;
  detail?: string;
}

export interface RepairSource {
  failedAttemptId: string;
  responseArtifactId: string;
  validationArtifactId: string;
  reusedCandidateArtifactIds: Partial<Record<ServerStageName, string>>;
}

export interface CanonicalSnapshot {
  projectId: string;
  projectRevision: number;
  brief: ProjectBrief;
  stageHeads: Record<ServerStageName, StageHead>;
  snapshotHash: string;
  capturedAt: string;
}

export interface PipelineRun {
  id: string;
  projectId: string;
  kind: "pipeline" | "rebuild" | "repair";
  parentRunId: string | null;
  repairStage: ServerStageName | null;
  repairSource: RepairSource | null;
  workUnitRepairScopeId: string | null;
  providerSnapshot: Record<string, unknown>;
  status: RunStatus;
  requestedStages: ServerStageName[];
  canonicalSnapshot: CanonicalSnapshot;
  instructions: string | null;
  legacyUnsealed: boolean;
  resultRevisionIds: string[];
  error: string | null;
  failureCode: string | null;
  failedStage: ServerStageName | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

/**
 * The polling projection deliberately excludes prompt text, provider response
 * bodies, validation payloads, and artifact content. Those remain available
 * only from the on-demand provenance endpoints.
 */
export interface RunProgressAttempt {
  attemptId: string;
  attemptNumber: number;
  attemptKind: "primary" | "correction";
  sourceAttemptId: string | null;
  status: "running" | "succeeded" | "failed" | "cancelled";
  outcomeCode: string | null;
  outcomeUnknown: boolean;
  startedAt: string | null;
  finishedAt: string | null;
  inputTokens: number | null;
  outputTokens: number | null;
  durationMs: number | null;
}

export interface RunProgressWorkUnit {
  workUnitId: string;
  stage: ServerStageName;
  sequence: number;
  /** Frozen attempt budget: primary plus the profile's correction allowance. */
  maxAttempts: number;
  status: GenerationWorkUnitTrace["status"];
  latestAttempt: RunProgressAttempt | null;
  sealed: boolean;
  repairEligible: boolean;
  repairReasonCode: string | null;
}

export interface RunProgressStage {
  stage: ServerStageName;
  stagePlanId: string | null;
  stagePlanHash: string | null;
  sealed: boolean;
  unitCount: number;
  completedUnitCount: number;
  quarantinedUnitCount: number;
  repairEligibleUnitIds: string[];
}

export interface RunProgress {
  runId: string;
  status: RunStatus;
  failureCode: string | null;
  failedStage: ServerStageName | null;
  stageProgress: RunProgressStage[];
  workUnits: RunProgressWorkUnit[];
  actions: {
    canResume: boolean;
    canCancel: boolean;
    canRebuildStage: boolean;
    repairEligible: boolean;
  };
}

export interface GenerationAttempt {
  id: string;
  runId: string;
  workUnitId: string | null;
  stage: ServerStageName;
  attemptNumber: number;
  attemptKind: "primary" | "correction";
  sourceAttemptId: string | null;
  status: "running" | "succeeded" | "failed" | "cancelled";
  provider: string | null;
  model: string | null;
  error: string | null;
  dispatchedAt: string | null;
  responsePersistedAt: string | null;
  providerRequestId: string | null;
  outcomeUnknown: boolean;
  outcomeCode: string | null;
  startedAt: string;
  finishedAt: string | null;
}

export interface RunArtifact {
  id: string;
  runId: string;
  attemptId: string | null;
  workUnitId: string | null;
  sourceArtifactId: string | null;
  stage: ServerStageName | null;
  kind: "prompt" | "response" | "validation" | "candidate" | "canonical" | "media";
  mediaType: string;
  content: unknown;
  contentHash: string;
  createdAt: string;
}

export interface RunTrace {
  run: PipelineRun;
  attempts: GenerationAttempt[];
  artifacts: RunArtifact[];
  snapshotIsCurrent: boolean;
}

export interface GenerationPlanTrace {
  runId: string;
  planHash: string;
  plan: Record<string, unknown>;
}

export interface StagePlanTrace {
  id: string;
  runId: string;
  stage: ServerStageName;
  stagePlanHash: string;
  dependencyHash: string;
  plan: Record<string, unknown>;
}

export interface GenerationWorkUnitTrace {
  id: string;
  runId: string;
  stagePlanId: string;
  stage: ServerStageName;
  sequence: number;
  selector: Record<string, unknown>;
  inputHash: string;
  dependencyHash: string;
  unitDependencyHash: string;
  budget: Record<string, unknown>;
  estimatedInputTokens: number;
  contextWindowTokens: number;
  status: "queued" | "running" | "succeeded" | "failed" | "quarantined" | "cancelled" | "outcome_unknown";
}

export interface SealedStageAggregateTrace {
  id: string;
  runId: string;
  stagePlanId: string;
  stage: ServerStageName;
  manifestHash: string;
  manifest: Record<string, unknown>;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface StoryGraphTopologyTrace {
  runId: string;
  generationPlanHash: string;
  topologyHash: string;
  topology: Record<string, unknown>;
  createdAt: string;
}

export interface RunExecutionTrace {
  generationPlan: GenerationPlanTrace | null;
  storyGraphTopology: StoryGraphTopologyTrace | null;
  stagePlans: StagePlanTrace[];
  workUnits: GenerationWorkUnitTrace[];
  sealedAggregates: SealedStageAggregateTrace[];
}

export interface ProjectRunsResponse {
  runs: PipelineRun[];
}

export interface MediaTask {
  id: string;
  projectId: string;
  shotId: string;
  storyboardRevision: number;
  kind: MediaKind;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  derivedPrompt: string;
  promptComponents: Record<string, unknown>;
  provider: string | null;
  publicSettings: Record<string, unknown>;
  providerTaskId: string | null;
  outputUri: string | null;
  error: string | null;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface ProjectMediaTasksResponse {
  tasks: MediaTask[];
}

export interface ProviderSettings {
  profileId: string;
  profileVersion: number;
  profileHash: string;
  redirectPolicy: "no_follow";
  textProvider: string | null;
  textBaseUrl: string | null;
  textModel: string | null;
  textAuthMode: "none" | "bearer";
  textCapabilities: { chatCompletions: boolean; jsonObject: boolean; jsonSchema: boolean };
  textContextWindowTokens: number;
  textMaxOutputTokens: number;
  textTemperature: number;
  textMaxConcurrency: number;
  textConnectTimeoutSeconds: number;
  textAttemptTimeoutSeconds: number;
  imageProvider: string | null;
  imageBaseUrl: string | null;
  imageModel: string | null;
  imageAuthMode: "none" | "bearer";
  videoProvider: string | null;
  videoBaseUrl: string | null;
  videoModel: string | null;
  videoAuthMode: "none" | "bearer";
  textKeyAvailable: boolean;
  imageKeyAvailable: boolean;
  videoKeyAvailable: boolean;
  revision: number;
  updatedAt: string | null;
}

export type ProviderSettingsUpdate = Partial<Pick<ProviderSettings,
  "textProvider" | "textBaseUrl" | "textModel" | "textAuthMode" | "textCapabilities" |
  "textContextWindowTokens" | "textMaxOutputTokens" | "textTemperature" | "textMaxConcurrency" |
  "textConnectTimeoutSeconds" | "textAttemptTimeoutSeconds" |
  "imageProvider" | "imageBaseUrl" | "imageModel" | "imageAuthMode" |
  "videoProvider" | "videoBaseUrl" | "videoModel" | "videoAuthMode"
>> & {
  expectedProfileId: string;
  expectedRevision: number;
};

export type TextProviderPresetId = "compatible_v1" | "quality_reasoning_v1" | "final_only_v1" | "custom";
export type TextProviderRequestExtension = "none" | "chat_template_kwargs";
export type TextProviderReasoningMode = "provider_default" | "enabled" | "disabled";

/** The secret-free configuration frozen into a named text-provider profile. */
export interface TextProviderProfileConfiguration {
  profileSchemaVersion: 2;
  profileId: string;
  profileVersion: number;
  profileHash: string;
  textProvider: string;
  textBaseUrl: string;
  textModel: string;
  textAuthMode: "none" | "bearer";
  textCapabilities: {
    chatCompletions: boolean;
    jsonObject: boolean;
    jsonSchema: boolean;
    chatTemplateKwargs: boolean;
  };
  textContextWindowTokens: number;
  textMaxOutputTokens: number;
  textTemperature: number;
  textMaxConcurrency: number;
  textConnectTimeoutSeconds: number;
  textAttemptTimeoutSeconds: number;
  redirectPolicy: "no_follow";
  requestExtension: TextProviderRequestExtension;
  reasoningMode: TextProviderReasoningMode;
  extractionPolicy: { allowJsonFence: boolean; allowLeadingThinkBlock: boolean };
  stageMaxOutputTokens: Record<ServerStageName, number>;
  maxSemanticCorrections: number;
  presetId: TextProviderPresetId;
  presetVersion: string;
}

export interface TextProviderProfileView {
  profileId: string;
  displayName: string;
  configuration: TextProviderProfileConfiguration;
  revision: number;
  enabled: boolean;
  availabilityRevision: number;
  adapterId: string;
  adapterVersion: string;
  createdAt: string;
  updatedAt: string;
  serverKeyAvailable: boolean;
  readiness: TextBackendReadiness;
}

export interface TextBackendReadiness {
  profileId: string;
  profileRevision: number;
  state: "disabled" | "missing_configuration" | "unverified" | "checking" | "available" | "unreachable" | "authentication_failed" | "model_mismatch" | "capability_mismatch";
  reasonCode: string;
  observedAt: string | null;
}

export interface TextProviderProfilesResponse {
  profiles: TextProviderProfileView[];
  activeProfileId: string;
  selectionRevision: number;
  presets: Record<Exclude<TextProviderPresetId, "custom">, TextProviderPresetValues>;
  trustedAdapters?: Array<{ adapterId: string; adapterVersion: string }>;
}

/** The optimistic-concurrency result of selecting the server's active profile. */
export interface TextProviderProfileSelection {
  activeProfileId: string;
  revision: number;
  updatedAt: string;
}

export interface TextProviderPresetValues {
  presetId: Exclude<TextProviderPresetId, "custom">;
  presetVersion: string;
  requestExtension: TextProviderRequestExtension;
  reasoningMode: TextProviderReasoningMode;
  textContextWindowTokens: number;
  textMaxOutputTokens: number;
  stageMaxOutputTokens: Record<ServerStageName, number>;
  textAttemptTimeoutSeconds: number;
  maxSemanticCorrections: number;
}

export interface TextProviderProfileCreate {
  profileId: string;
  displayName: string;
  configuration?: TextProviderProfileConfiguration;
  copyFromProfileId?: string;
  adapterId?: string;
  adapterVersion?: string;
}

export interface TextProviderProfileProbe {
  profileId: string;
  profileRevision: number;
  state: TextBackendReadiness["state"];
  reasonCode: string;
  observedAt: string | null;
}

export type SourceKind = "synopsis" | "imported_text" | "existing_work";

export interface SourceMaterial {
  kind: SourceKind;
  title: string;
  text: string;
  attribution: string | null;
  rightsDeclaration: string | null;
  adaptationIntent: string;
  inventedAdditions: string | null;
}

export interface SourceRevision {
  revision: number;
  contentHash: string;
  material: SourceMaterial;
  createdAt: string;
}

export interface OutlineCandidate {
  jobId: string;
  sourceRevision: number;
  expectedOutlineRevision: number;
  status: "prepared" | "ready" | "accepted" | "cancelled";
  deliveryId: string | null;
  manifestHash: string | null;
  outline: Record<string, unknown> | null;
  reportAvailable: boolean;
  createdAt: string;
  deliveredAt: string | null;
}

export interface OutlineCandidatePreparation extends OutlineCandidate {
  packagePath: string;
  deliveryPath: string;
  assignment: string;
}

export interface AcceptedOutlineRevision {
  revision: number;
  sourceRevision: number;
  candidateJobId: string;
  contentHash: string;
  outline: Record<string, unknown>;
  acceptedAt: string;
}

export interface SourceOutlineReviewState {
  source: SourceRevision | null;
  candidate: OutlineCandidate | null;
  acceptedOutline: AcceptedOutlineRevision | null;
  outlineStatus: "missing" | "candidate_ready" | "accepted" | "reopened";
  acceptedSectionMap: AcceptedSectionMapRevision | null;
  sectionMapStatus: "missing" | "current" | "stale";
  sectionMapStaleReasons: string[];
  graphAdmission: SourceMapGraphAdmission | null;
}

export interface StorySection { sectionId: string; title: string; summary: string; ending: boolean; }
export interface BranchOutcome { outcomeId: string; label: string; consequence: string; endingSectionId: string; }
export interface SectionChoice { choiceId: string; sectionId: string; prompt: string; outcomes: [BranchOutcome, BranchOutcome]; }
export interface SectionMap { sections: StorySection[]; choice: SectionChoice; }
export interface AcceptedSectionMapRevision {
  revision: number; sourceRevision: number; outlineRevision: number; outlineContentHash: string;
  contentHash: string; mapping: SectionMap; acceptedAt: string;
}
export interface SourceMapGraphAdmission {
  sourceRevision: number; sourceContentHash: string; outlineRevision: number; outlineContentHash: string;
  sectionMapRevision: number; sectionMapContentHash: string; graphRevision: number; graphContentHash: string;
  status: "current" | "stale"; staleReasons: string[]; installedAt: string;
}
export interface CastBinding { sourceRevision: number; sourceContentHash: string; outlineRevision: number; outlineContentHash: string; sectionMapRevision: number; sectionMapContentHash: string; graphRevision: number; graphContentHash: string; sectionIds: string[]; }
export interface CastCandidate { jobId: string; expectedCastRevision: number; binding: CastBinding; status: "prepared" | "ready" | "accepted" | "cancelled"; deliveryId: string | null; manifestHash: string | null; cast: Record<string, unknown> | null; reportAvailable: boolean; createdAt: string; deliveredAt: string | null; }
export interface CastCandidatePreparation extends CastCandidate { packagePath: string; deliveryPath: string; assignment: string; }
export interface AcceptedCastRevision { revision: number; candidateJobId: string; contentHash: string; binding: CastBinding; cast: Record<string, unknown>; consumerMappings: Array<{ castCharacterId: string; consumerCharacterId: string }>; acceptedAt: string; }
export interface CastReviewState { candidate: CastCandidate | null; acceptedCast: AcceptedCastRevision | null; status: "missing" | "prepared" | "candidate_ready" | "accepted" | "reopened" | "stale"; staleReasons: string[]; }
export interface ArtBinding extends CastBinding { castRevision: number; castContentHash: string; }
export interface ArtCandidate { jobId: string; expectedArtRevision: number; binding: ArtBinding; status: "prepared" | "ready" | "accepted" | "cancelled"; deliveryId: string | null; manifestHash: string | null; art: Record<string, unknown> | null; reportAvailable: boolean; createdAt: string; deliveredAt: string | null; }
export interface ArtCandidatePreparation extends ArtCandidate { packagePath: string; deliveryPath: string; assignment: string; }
export interface AcceptedArtRevision { revision: number; candidateJobId: string; contentHash: string; binding: ArtBinding; art: Record<string, unknown>; acceptedAt: string; }
export interface ArtReviewState { candidate: ArtCandidate | null; acceptedArt: AcceptedArtRevision | null; status: "missing" | "prepared" | "candidate_ready" | "accepted" | "reopened" | "stale"; staleReasons: string[]; }

export interface ScriptBinding extends ArtBinding {
  artRevision: number;
  artContentHash: string;
  targetPlaythroughSeconds: number;
  timingAllocationHash: string;
  sectionBindings: Array<{ sectionId: string; episode: number }>;
  sectionDurationCaps: Array<{ sectionId: string; durationCapMilliseconds: number }>;
  completeRouteSectionIds: string[][];
}
export interface ScriptCandidate { jobId: string; expectedScriptRevision: number; binding: ScriptBinding; status: "prepared" | "ready" | "accepted" | "cancelled"; deliveryId: string | null; manifestHash: string | null; script: Record<string, unknown> | null; reportAvailable: boolean; createdAt: string; deliveredAt: string | null; }
export interface ScriptCandidatePreparation extends ScriptCandidate { packagePath: string; deliveryPath: string; assignment: string; }
export interface AcceptedScriptRevision { revision: number; candidateJobId: string; contentHash: string; binding: ScriptBinding; script: Record<string, unknown>; acceptedAt: string; }
export interface ScriptReviewState { candidate: ScriptCandidate | null; acceptedScript: AcceptedScriptRevision | null; status: "missing" | "prepared" | "candidate_ready" | "accepted" | "reopened" | "stale"; staleReasons: string[]; }
export interface StoryboardReviewBinding extends ScriptBinding { scriptRevision: number; scriptContentHash: string; reviewMinCutSeconds: number; reviewMaxCutSeconds: number; reviewMaxSegmentSeconds: number; }
export interface StoryboardReviewCandidate { jobId: string; expectedReviewRevision: number; binding: StoryboardReviewBinding; status: "prepared" | "ready" | "accepted" | "cancelled"; deliveryId: string | null; manifestHash: string | null; storyboard: Record<string, unknown> | null; reportAvailable: boolean; createdAt: string; deliveredAt: string | null; }
export interface StoryboardReviewCandidatePreparation extends StoryboardReviewCandidate { packagePath: string; deliveryPath: string; assignment: string; }
export interface AcceptedStoryboardReviewRevision { revision: number; candidateJobId: string; contentHash: string; binding: StoryboardReviewBinding; storyboard: Record<string, unknown>; acceptedAt: string; }
export interface StoryboardReviewState { candidate: StoryboardReviewCandidate | null; acceptedReview: AcceptedStoryboardReviewRevision | null; status: "missing" | "prepared" | "candidate_ready" | "accepted" | "stale"; staleReasons: string[]; }
export interface ProductionBridgeConflict { code: string; message: string; sectionId: string | null; episode: number | null; sceneIndex: number | null; }
export interface ProductionBridgeIntentEntry { id: string; targetKind: "scene_objective" | "beat_purpose"; targetId: string; sourceCoordinates: Record<string, unknown>; sourceContentHash: string; sourceExcerpt: string; suggestedText: string | null; text: string; }
export interface ProductionBridgeIntentPackage { suggestionOrigin: "none" | "model_inference.v1"; reviewState: "pending" | "model_suggested" | "author_saved"; entries: ProductionBridgeIntentEntry[]; provenance?: Record<string, unknown> | null; }
export interface ProductionBridgeProposal { revision: number; contentHash: string; inputs: Record<string, unknown>; intentPackage: ProductionBridgeIntentPackage; scenes: Array<Record<string, unknown>>; cuts: Array<Record<string, unknown>>; conflicts: ProductionBridgeConflict[]; advisories: ProductionBridgeConflict[]; installable: boolean; preparedAt: string; }
export interface ProductionBridgeIntentJob { id: string; status: "queued" | "dispatched" | "ready" | "stale" | "failed" | "cancelled" | "outcome_unknown"; proposalRevision: number; proposalContentHash: string; profileId: string; profileVersion: number; promptVersion: string; createdAt: string; updatedAt: string; errorCode: string | null; errorMessage: string | null; resultProposalRevision: number | null; providerRequestId: string | null; responseHash: string | null; }
export interface ProductionBridgeState { proposal: ProductionBridgeProposal | null; status: "missing" | "ready" | "accepted" | "stale"; staleReasons: string[]; installedStageRevisions: Record<string, number> | null; installedStoryboardCurrent: boolean; intentJob?: ProductionBridgeIntentJob | null; simulationLabel?: string | null; }
