export type StageName = "project_brief" | "story_bible" | "story_graph" | "scene_beats" | "storyboard";
export type ServerStageName = Exclude<StageName, "project_brief">;
export type RunStatus = "queued" | "running" | "succeeded" | "quarantined" | "cancel_requested" | "cancelled" | "failed";
export type MediaKind = "image" | "video";

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
}

export interface CharacterCard {
  id: string;
  name: string;
  role: string | null;
  description: string;
  goal: string;
  traits: string[];
  visualIdentity: string;
  continuityRules: string[];
}

export interface LocationCard {
  id: string;
  name: string;
  description: string;
  visualIdentity: string;
  continuityRules: string[];
}

export interface PropCard {
  id: string;
  name: string;
  description: string;
  visualIdentity: string;
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
  characterStates: Record<string, string>;
  propStates: Record<string, string>;
  locationState: string | null;
  screenDirection: string | null;
  lighting: string | null;
  sound: string | null;
  notes: string[];
}

export interface DramaticScene {
  id: string;
  storyNodeId: string;
  title: string;
  objective: string;
  locationId: string | null;
  characterIds: string[];
  beatIds: string[];
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
  dialogue: string;
  immediateResult: string;
  dramaticChange: string;
  entryState: ContinuityState;
  exitState: ContinuityState;
  continuityAnchors: string[];
  continuityDelta: Record<string, unknown>;
}

export interface SceneBeatPlan {
  scenes: DramaticScene[];
  beats: Beat[];
}

export interface Shot {
  id: string;
  sceneId: string;
  order: number;
  title: string;
  shotSize: "extreme_wide" | "wide" | "full" | "medium" | "close_up" | "extreme_close_up" | "insert";
  durationSeconds: number;
  cameraAngle: string;
  cameraMovement: string;
  composition: string;
  visualIntent: string;
  motionIntent: string;
  action: string;
  dialogue: string;
  audio: string;
  transition: string;
  characterIds: string[];
  locationId: string | null;
  propIds: string[];
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

export interface QuarantineItem {
  id: string;
  stage: ServerStageName;
  code: string;
  message: string;
  rawOutput: string;
  repairHint: string;
}

export interface WorkspaceProject {
  id?: string;
  revision: number;
  updatedAt?: string;
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
  createdAt: string;
  updatedAt: string;
  serverKeyAvailable: boolean;
}

export interface TextProviderProfilesResponse {
  profiles: TextProviderProfileView[];
  activeProfileId: string;
  selectionRevision: number;
  presets: Record<Exclude<TextProviderPresetId, "custom">, TextProviderPresetValues>;
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
}

export interface TextProviderProfileProbe {
  profileId: string;
  model: string | null;
  finalContentPresent: boolean;
  reasoningPresent: boolean;
  finishReason: string | null;
  latencyMs: number;
  errorCode: string | null;
}
