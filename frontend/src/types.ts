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
  resultRevisionIds: string[];
  error: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface GenerationAttempt {
  id: string;
  runId: string;
  stage: ServerStageName;
  attemptNumber: number;
  status: "running" | "succeeded" | "failed" | "cancelled";
  provider: string | null;
  model: string | null;
  error: string | null;
  startedAt: string;
  finishedAt: string | null;
}

export interface RunArtifact {
  id: string;
  runId: string;
  attemptId: string | null;
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
  textProvider: string | null;
  textBaseUrl: string | null;
  textModel: string | null;
  imageProvider: string | null;
  imageBaseUrl: string | null;
  imageModel: string | null;
  videoProvider: string | null;
  videoBaseUrl: string | null;
  videoModel: string | null;
  textKeyAvailable: boolean;
  imageKeyAvailable: boolean;
  videoKeyAvailable: boolean;
  revision: number;
  updatedAt: string | null;
}

export type ProviderSettingsUpdate = Partial<Pick<ProviderSettings,
  "textProvider" | "textBaseUrl" | "textModel" |
  "imageProvider" | "imageBaseUrl" | "imageModel" |
  "videoProvider" | "videoBaseUrl" | "videoModel"
>>;
