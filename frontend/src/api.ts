import type {
  MediaKind,
  MediaTask,
  ProjectCreationRequest,
  ProjectCreationResponse,
  ProjectDuplicateResponse,
  PipelineRun,
  ProjectBrief,
  AuthoringDraft,
  AuthoringDraftScope,
  CanonicalDraftConsumption,
  ProjectMediaTasksResponse,
  ProjectListResponse,
  ProjectResource,
  ProjectSnapshotReceipt,
  ProjectRunsResponse,
  ProviderSettings,
  ProviderSettingsUpdate,
  ServerStageName,
  TextProviderProfileCreate,
  TextProviderProfileProbe,
  TextProviderProfileSelection,
  TextProviderProfilesResponse,
  TextProviderProfileView,
  TextProviderProfileConfiguration,
  StageEnvelopesResponse,
  StageHead,
  RunExecutionTrace,
  RunProgress,
  RunTrace,
  StoryboardReview,
  ApprovalClosure,
  ManagedAsset,
  ImageJob,
  ImageJobsResponse,
  CharacterReferencesResponse,
  CharacterReferenceDecision,
  CharacterReferenceProposalsResponse,
  CharacterReferenceProposal,
  SamePersonReviewsResponse,
  SamePersonReview,
  StillPreview,
  VisualWorkbench,
  VisualIntent,
  VideoJob,
  VideoBackend,
  VideoPilotBudget,
  SourceMaterial,
  SourceOutlineReviewState,
  SectionMap,
  OutlineCandidate,
  OutlineCandidatePreparation,
  CastReviewState,
  CastCandidate,
  CastCandidatePreparation,
  ArtReviewState,
  ArtCandidate,
  ArtCandidatePreparation,
  ArtReferenceProposal,
  ArtReferenceProposalsResponse,
  ScriptReviewState,
  ScriptCandidate,
  ScriptCandidatePreparation,
  StoryboardReviewState,
  StoryboardReviewCandidate,
  StoryboardReviewCandidatePreparation,
} from "./types";
import { providerSessionKeys } from "./session-key";
import { projectCreationBody } from "./project-creation";

type FetchLike = typeof fetch;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class PlotloomApiClient {
  private readonly fetcher: FetchLike;
  private readonly base: string;

  constructor(
    fetcher: FetchLike = globalThis.fetch,
    base = "/api/v2",
  ) {
    // Window.fetch is a Web-IDL method and some browsers reject a foreign
    // receiver. Keep the injected function in a closure and always invoke it
    // with the platform global rather than as `this.fetcher(...)`.
    this.fetcher = (input, init) => fetcher.call(globalThis, input, init);
    this.base = base;
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    includeSessionKey = false,
    sessionProfileId = "default",
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    if (includeSessionKey) {
      const ephemeralKey = providerSessionKeys.read(sessionProfileId);
      if (ephemeralKey) headers.set("X-Plotloom-Session-API-Key", ephemeralKey);
    }
    const response = await this.fetcher(`${this.base}${path}`, { ...init, headers });
    const body = await response.json().catch(() => undefined);
    if (!response.ok) {
      const message = body && typeof body === "object" && "message" in body
        ? String(body.message)
        : `Plotloom API request failed (${response.status})`;
      throw new ApiError(message, response.status, body);
    }
    return body as T;
  }

  /** Preserve an exact draft-consumption receipt without widening canonical bodies. */
  private async requestWithResponse<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<{ body: T; response: Response }> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    const response = await this.fetcher(`${this.base}${path}`, { ...init, headers });
    const body = await response.json().catch(() => undefined);
    if (!response.ok) {
      const message = body && typeof body === "object" && "message" in body
        ? String(body.message)
        : `Plotloom API request failed (${response.status})`;
      throw new ApiError(message, response.status, body);
    }
    return { body: body as T, response };
  }

  createProject(request: ProjectCreationRequest, idempotencyKey: string): Promise<ProjectCreationResponse> {
    return this.request("/projects", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: projectCreationBody(request),
    });
  }

  getProject(projectId: string, signal?: AbortSignal): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}`, { signal });
  }

  listProjects(includeArchived = false, limit = 50, cursor?: string): Promise<ProjectListResponse> {
    const query = new URLSearchParams({
      status: includeArchived ? "all" : "active",
      limit: String(limit),
    });
    if (cursor) query.set("cursor", cursor);
    return this.request(`/projects?${query.toString()}`);
  }

  archiveProject(projectId: string, expectedLifecycleRevision: number): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/archive`, {
      method: "POST", body: JSON.stringify({ expectedLifecycleRevision }),
    });
  }

  restoreProject(projectId: string, expectedLifecycleRevision: number): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/restore`, {
      method: "POST", body: JSON.stringify({ expectedLifecycleRevision }),
    });
  }

  closeProject(projectId: string): Promise<{ projectId: string; state: "closed"; revision: number }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/close`, { method: "POST" });
  }

  openProjectFolder(projectId: string): Promise<{ projectId: string; state: "open"; revision: number }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/open`, { method: "POST" });
  }

  createProjectSnapshot(projectId: string): Promise<ProjectSnapshotReceipt> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/snapshots`, { method: "POST" });
  }

  getProjectSnapshot(projectId: string, snapshotId: string): Promise<ProjectSnapshotReceipt> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/snapshots/${encodeURIComponent(snapshotId)}`);
  }

  duplicateProject(projectId: string, expectedLifecycleRevision: number, title?: string, idempotencyKey?: string): Promise<ProjectDuplicateResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/duplicate`, {
      method: "POST", headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      body: JSON.stringify({ expectedLifecycleRevision, ...(title ? { title } : {}) }),
    });
  }

  permanentlyDeleteProject(projectId: string, expectedLifecycleRevision: number, confirmationTitle: string): Promise<void> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/permanent-delete`, {
      method: "POST", body: JSON.stringify({ expectedLifecycleRevision, confirmationTitle }),
    });
  }

  patchProject(projectId: string, expectedRevision: number, brief: ProjectBrief): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, brief }),
    });
  }

  async patchProjectWithDraft(
    projectId: string,
    expectedRevision: number,
    brief: ProjectBrief,
    consumedDraft: CanonicalDraftConsumption,
  ): Promise<{ project: ProjectResource; consumedDraftRevision?: number }> {
    const result = await this.requestWithResponse<ProjectResource>(`/projects/${encodeURIComponent(projectId)}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, brief, consumedDraft }),
    });
    const receipt = result.response.headers.get("X-Plotloom-Draft-Consumed-Revision");
    return { project: result.body, consumedDraftRevision: receipt ? Number(receipt) : undefined };
  }

  getStages(projectId: string, signal?: AbortSignal): Promise<StageEnvelopesResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/stages`, { signal });
  }

  getStoryboardReview(projectId: string, signal?: AbortSignal): Promise<StoryboardReview> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-review`, { signal });
  }

  decideStoryboardApproval(projectId: string, body: {
    expectedRevision: number; contentHash: string; decision: "approve" | "revoke";
    reviewer: string; gateSetVersion: string; note?: string;
  }): Promise<ApprovalClosure> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-approval`, {
      method: "POST", body: JSON.stringify(body),
    });
  }

  getProjectRuns(projectId: string, signal?: AbortSignal): Promise<ProjectRunsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/runs`, { signal });
  }

  getProjectMediaTasks(projectId: string, signal?: AbortSignal): Promise<ProjectMediaTasksResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/media-tasks`, { signal });
  }

  getVisualWorkbench(projectId: string, signal?: AbortSignal): Promise<VisualWorkbench> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/visual-workbench`, { signal });
  }

  getImageJobs(projectId: string, signal?: AbortSignal): Promise<ImageJobsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs`, { signal });
  }

  prepareImageJob(projectId: string, body: {
    approvalId: string; shotId: string; storyboardRevision: number; parentCandidateAssetId?: string; keyframeAdaptationProfileId?: string; presentationChange: string; contractVersion?: 2 | 3;
    contextId?: string; consumedDraft?: CanonicalDraftConsumption;
  }): Promise<{ job: ImageJob }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs`, { method: "POST", body: JSON.stringify(body) });
  }

  copyImageJob(projectId: string, jobId: string): Promise<{ job: ImageJob; assignment: string; packagePath: string; deliveryPath: string }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/copy`, { method: "POST" });
  }

  refreshImageJob(projectId: string, jobId: string): Promise<{ state: "awaiting_delivery" | "accepted" | "inapplicable"; candidates: Array<{ assetId: string }> }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/refresh`, { method: "POST" });
  }

  cancelImageJob(projectId: string, jobId: string, reason: string): Promise<ImageJob> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
  }

  createReviewedKeyframeCenterCrop(projectId: string, bindingId: string, body: {
    targetProfileId: string; expectedSelectionRevision: number;
  }): Promise<{ asset: ManagedAsset }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/reviewed-keyframes/${encodeURIComponent(bindingId)}/center-crops`, { method: "POST", body: JSON.stringify(body) });
  }

  getCharacterReferences(projectId: string, signal?: AbortSignal): Promise<CharacterReferencesResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-references`, { signal });
  }

  selectCharacterReference(projectId: string, body: {
    characterId: string; authority: "cast" | "story_bible"; primaryAssetId: string; complementaryAssetIds: string[]; expectedReferenceRevision: number; reviewer: string; notes: string;
  }): Promise<CharacterReferenceDecision> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-references`, { method: "POST", body: JSON.stringify(body) });
  }

  revokeCharacterReference(projectId: string, characterId: string, body: {
    expectedReferenceRevision: number; reviewer: string; reason: string;
  }): Promise<CharacterReferenceDecision> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-references/${encodeURIComponent(characterId)}/revoke`, { method: "POST", body: JSON.stringify(body) });
  }

  getCharacterReferenceProposals(projectId: string, signal?: AbortSignal): Promise<CharacterReferenceProposalsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-reference-proposals`, { signal });
  }

  prepareCharacterReferenceProposal(projectId: string, body: {
    characterId: string; castRevision: number; visualDirection: string; parentCandidateAssetId?: string;
  }): Promise<{ proposal: CharacterReferenceProposal }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-reference-proposals`, { method: "POST", body: JSON.stringify(body) });
  }

  copyCharacterReferenceProposal(projectId: string, proposalId: string): Promise<{ proposal: CharacterReferenceProposal; assignment: string; packagePath: string; deliveryPath: string }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-reference-proposals/${encodeURIComponent(proposalId)}/copy`, { method: "POST" });
  }

  cancelCharacterReferenceProposal(projectId: string, proposalId: string, reason: string): Promise<CharacterReferenceProposal> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-reference-proposals/${encodeURIComponent(proposalId)}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
  }

  refreshCharacterReferenceProposal(projectId: string, proposalId: string): Promise<{ state: "awaiting_delivery" | "accepted" | "inapplicable"; candidates: CharacterReferenceProposal["deliveries"][number]["candidates"] }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/character-reference-proposals/${encodeURIComponent(proposalId)}/refresh`, { method: "POST" });
  }

  getArtReferenceProposals(projectId: string, signal?: AbortSignal): Promise<ArtReferenceProposalsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/art-reference-proposals`, { signal });
  }

  prepareArtReferenceProposal(projectId: string, body: { subjectType: "scene" | "prop"; subjectId: string; renderDirection: string }): Promise<{ proposal: ArtReferenceProposal }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/art-reference-proposals`, { method: "POST", body: JSON.stringify(body) });
  }

  copyArtReferenceProposal(projectId: string, proposalId: string): Promise<{ proposal: ArtReferenceProposal; assignment: string; packagePath: string; deliveryPath: string }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/art-reference-proposals/${encodeURIComponent(proposalId)}/copy`, { method: "POST" });
  }

  refreshArtReferenceProposal(projectId: string, proposalId: string): Promise<{ state: "awaiting_delivery" | "accepted" | "inapplicable"; candidates: ArtReferenceProposal["deliveries"][number]["candidates"] }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/art-reference-proposals/${encodeURIComponent(proposalId)}/refresh`, { method: "POST" });
  }

  cancelArtReferenceProposal(projectId: string, proposalId: string, reason: string): Promise<ArtReferenceProposal> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/art-reference-proposals/${encodeURIComponent(proposalId)}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
  }

  getSamePersonReviews(projectId: string, signal?: AbortSignal): Promise<SamePersonReviewsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/same-person-reviews`, { signal });
  }

  recordSamePersonReview(projectId: string, body: {
    bindingId: string; expectedReviewRevision: number; reviewer: string;
    comparisons: Array<{ characterId: string; judgment: "pass" | "fail"; identityNotes: string; stateNotes: string }>;
    notes: string;
  }): Promise<SamePersonReview> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/same-person-reviews`, { method: "POST", body: JSON.stringify(body) });
  }

  importManagedAsset(projectId: string, file: File, declaration: {
    origin: string; rights: "known" | "unknown"; rightsNote?: string; declaredAdditions?: string[];
  }): Promise<ManagedAsset> {
    const form = new FormData();
    form.set("image", file);
    form.set("origin", declaration.origin);
    form.set("rights", declaration.rights);
    if (declaration.rightsNote) form.set("rights_note", declaration.rightsNote);
    form.set("declared_additions_json", JSON.stringify(declaration.declaredAdditions ?? []));
    return this.request(`/projects/${encodeURIComponent(projectId)}/managed-assets`, { method: "POST", body: form });
  }

  managedAssetUrl(projectId: string, assetId: string, variant: "display" | "original" = "display"): string {
    return `${this.base}/projects/${encodeURIComponent(projectId)}/managed-assets/${encodeURIComponent(assetId)}/${variant}`;
  }

  createVisualIntent(projectId: string, assetId: string, body: {
    role: "protagonist_reference" | "location_reference" | "shot_keyframe";
    identityIntent?: string; compositionIntent?: string; styleIntent?: string;
    sourceRefs?: string[];
    shotId?: string; consumedDraft?: CanonicalDraftConsumption;
  }): Promise<VisualIntent> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/managed-assets/${encodeURIComponent(assetId)}/visual-intents`, {
      method: "POST", body: JSON.stringify(body),
    });
  }

  selectReviewedKeyframe(projectId: string, body: {
    assetId: string; shotId: string; sceneId: string; expectedSelectionRevision: number;
    storyboardRevision: number; approvalId: string; compatibilityNote: string;
    visualIntentId: string; visualIntentRevision: number;
  }): Promise<{ id: string; selectionRevision: number }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/reviewed-keyframes`, { method: "POST", body: JSON.stringify(body) });
  }

  createStillPreview(projectId: string, body: {
    sceneId: string; shotIds: string[]; expectedSelectionRevision: number;
    storyboardRevision: number; approvalId: string;
  }): Promise<StillPreview> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/still-previews`, { method: "POST", body: JSON.stringify(body) });
  }

  patchStage<T>(projectId: string, stage: ServerStageName, expectedRevision: number, content: T): Promise<StageHead> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/stages/${stage}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, payload: content }),
    });
  }

  async patchStageWithDraft<T>(
    projectId: string,
    stage: ServerStageName,
    expectedRevision: number,
    content: T,
    consumedDraft: CanonicalDraftConsumption,
  ): Promise<{ stage: StageHead; consumedDraftRevision?: number }> {
    const result = await this.requestWithResponse<StageHead>(`/projects/${encodeURIComponent(projectId)}/stages/${stage}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, payload: content, consumedDraft }),
    });
    const receipt = result.response.headers.get("X-Plotloom-Draft-Consumed-Revision");
    return { stage: result.body, consumedDraftRevision: receipt ? Number(receipt) : undefined };
  }

  getAuthoringDraftCapability(): Promise<{
    durableProjectDrafts: boolean;
    /** Media buffers are project-owned only in the direct format-5 composition. */
    durableMediaDrafts?: boolean;
    /** True only for the direct project-folder composition. */
    explicitProjectClose?: boolean;
    /** True only when the backend can create a verified portable snapshot. */
    portableSnapshots?: boolean;
  }> {
    return this.request("/authoring-draft-capabilities");
  }

  getAuthoringDrafts(projectId: string, signal?: AbortSignal): Promise<AuthoringDraft[]> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/authoring-drafts`, { signal });
  }

  saveAuthoringDraft(
    projectId: string,
    body: {
      editorScope: AuthoringDraftScope; entityId: string; baseCanonicalRevision: number;
      expectedDraftRevision: number; payload: Record<string, unknown>;
    },
  ): Promise<AuthoringDraft> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/authoring-drafts`, {
      method: "PUT", body: JSON.stringify(body),
    });
  }

  async discardAuthoringDraft(
    projectId: string,
    body: { editorScope: AuthoringDraftScope; entityId: string; expectedDraftRevision: number },
  ): Promise<number | undefined> {
    const result = await this.requestWithResponse<void>(`/projects/${encodeURIComponent(projectId)}/authoring-drafts`, {
      method: "DELETE", body: JSON.stringify(body),
    });
    const receipt = result.response.headers.get("X-Plotloom-Draft-Consumed-Revision");
    return receipt ? Number(receipt) : undefined;
  }

  startRun(
    projectId: string,
    stages: ServerStageName[],
    providerProfileId = "default",
    includeSessionKey = true,
  ): Promise<PipelineRun> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/pipeline-runs`, {
      method: "POST",
      body: JSON.stringify({ stages, providerProfileId }),
    }, includeSessionKey, providerProfileId);
  }

  rebuild(
    projectId: string,
    fromStage: ServerStageName,
    providerProfileId = "default",
    includeSessionKey = true,
  ): Promise<PipelineRun> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/rebuilds`, {
      method: "POST",
      body: JSON.stringify({ fromStage, providerProfileId }),
    }, includeSessionKey, providerProfileId);
  }

  getRun(runId: string): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}`);
  }

  getTrace(runId: string): Promise<RunTrace> {
    return this.request(`/runs/${encodeURIComponent(runId)}/trace`);
  }

  getRunExecutionTrace(runId: string): Promise<RunExecutionTrace> {
    return this.request(`/runs/${encodeURIComponent(runId)}/execution-trace`);
  }

  /**
   * High-frequency status projection. This endpoint intentionally contains no
   * prompt, provider-response, validation-payload, or artifact content.
   */
  getRunProgress(runId: string): Promise<RunProgress> {
    return this.request(`/runs/${encodeURIComponent(runId)}/progress`);
  }

  resumeRun(runId: string, providerProfileId: string, includeSessionKey = true): Promise<PipelineRun> {
    return this.request(
      `/runs/${encodeURIComponent(runId)}/resume`,
      { method: "POST", body: "{}" },
      includeSessionKey,
      providerProfileId,
    );
  }

  cancelRun(runId: string): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST", body: "{}" });
  }

  /**
   * Exact work-unit repair inherits the parent run's frozen profile. The
   * request body is deliberately secret-free and cannot switch profile.
   */
  repairWorkUnit(
    runId: string,
    workUnitId: string,
    frozenProfileId: string,
    idempotencyKey: string,
    includeSessionKey = true,
  ): Promise<PipelineRun> {
    return this.request(
      `/runs/${encodeURIComponent(runId)}/work-units/${encodeURIComponent(workUnitId)}/repairs`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: "{}",
      },
      includeSessionKey,
      frozenProfileId,
    );
  }

  startMediaTask(projectId: string, shotId: string, kind: MediaKind): Promise<MediaTask> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/shots/${encodeURIComponent(shotId)}/media-tasks`, {
      method: "POST",
      body: JSON.stringify({ kind }),
    });
  }

  getMediaTask(taskId: string): Promise<MediaTask> {
    return this.request(`/media-tasks/${encodeURIComponent(taskId)}`);
  }

  getSourceOutline(projectId: string, signal?: AbortSignal): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline`, { signal });
  }

  saveSourceMaterial(projectId: string, expectedSourceRevision: number, material: SourceMaterial): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/source`, {
      method: "PUT", body: JSON.stringify({ expectedSourceRevision, material }),
    });
  }

  prepareOutlineCandidate(projectId: string): Promise<OutlineCandidatePreparation> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/candidates`, { method: "POST" });
  }

  refreshOutlineCandidate(projectId: string, jobId: string): Promise<OutlineCandidate> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/candidates/${encodeURIComponent(jobId)}/refresh`, { method: "POST" });
  }

  cancelOutlineCandidate(projectId: string, jobId: string): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/candidates/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
  }

  acceptOutlineCandidate(projectId: string, body: { jobId: string; expectedSourceRevision: number; expectedOutlineRevision: number }): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/accept`, { method: "POST", body: JSON.stringify(body) });
  }

  reopenOutline(projectId: string, expectedOutlineRevision: number): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/reopen`, { method: "POST", body: JSON.stringify({ expectedOutlineRevision }) });
  }

  saveSectionMap(projectId: string, body: { expectedSectionMapRevision: number; expectedSourceRevision: number; expectedOutlineRevision: number; expectedOutlineContentHash: string; mapping: SectionMap }): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/section-map`, { method: "PUT", body: JSON.stringify(body) });
  }

  installSectionMapGraph(projectId: string, body: { expectedSourceRevision: number; expectedSourceContentHash: string; expectedOutlineRevision: number; expectedOutlineContentHash: string; expectedSectionMapRevision: number; expectedSectionMapContentHash: string; expectedGraphRevision: number }): Promise<SourceOutlineReviewState> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/source-outline/section-map/install-graph`, { method: "POST", body: JSON.stringify(body) });
  }

  outlineCandidateReportUrl(projectId: string, jobId: string): string {
    return `${this.base}/projects/${encodeURIComponent(projectId)}/source-outline/candidates/${encodeURIComponent(jobId)}/report`;
  }

  getCast(projectId: string, signal?: AbortSignal): Promise<CastReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast`, { signal }); }
  prepareCastCandidate(projectId: string): Promise<CastCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/candidates`, { method: "POST" }); }
  refreshCastCandidate(projectId: string, jobId: string): Promise<CastCandidate> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/candidates/${encodeURIComponent(jobId)}/refresh`, { method: "POST" }); }
  cancelCastCandidate(projectId: string, jobId: string): Promise<CastReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/candidates/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }); }
  acceptCastCandidate(projectId: string, body: { jobId: string; expectedCastRevision: number; binding: unknown; consumerMappings: Array<{ castCharacterId: string; consumerCharacterId: string }>; cast: Record<string, unknown> }): Promise<CastReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/accept`, { method: "POST", body: JSON.stringify(body) }); }
  reopenCast(projectId: string, expectedCastRevision: number): Promise<CastReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/reopen`, { method: "POST", body: JSON.stringify({ expectedCastRevision }) }); }
  saveReopenedCast(projectId: string, body: { expectedCastRevision: number; binding: unknown; consumerMappings: Array<{ castCharacterId: string; consumerCharacterId: string }>; cast: Record<string, unknown> }): Promise<CastReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/cast/save`, { method: "POST", body: JSON.stringify(body) }); }
  castCandidateReportUrl(projectId: string, jobId: string): string { return `${this.base}/projects/${encodeURIComponent(projectId)}/cast/candidates/${encodeURIComponent(jobId)}/report`; }

  getArt(projectId: string): Promise<ArtReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/art`); }
  prepareArtCandidate(projectId: string): Promise<ArtCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/candidates`, { method: "POST" }); }
  recoverArtHandoff(projectId: string, jobId: string): Promise<ArtCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/candidates/${encodeURIComponent(jobId)}/handoff`); }
  refreshArtCandidate(projectId: string, jobId: string): Promise<ArtCandidate> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/candidates/${encodeURIComponent(jobId)}/refresh`, { method: "POST" }); }
  cancelArtCandidate(projectId: string, jobId: string): Promise<ArtReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/candidates/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }); }
  acceptArtCandidate(projectId: string, body: { jobId: string; expectedArtRevision: number; binding: unknown; art: Record<string, unknown> }): Promise<ArtReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/accept`, { method: "POST", body: JSON.stringify(body) }); }
  reopenArt(projectId: string, expectedArtRevision: number): Promise<ArtReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/reopen`, { method: "POST", body: JSON.stringify({ expectedArtRevision }) }); }
  saveReopenedArt(projectId: string, body: { expectedArtRevision: number; binding: unknown; art: Record<string, unknown> }): Promise<ArtReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/art/save`, { method: "POST", body: JSON.stringify(body) }); }
  artCandidateReportUrl(projectId: string, jobId: string): string { return `${this.base}/projects/${encodeURIComponent(projectId)}/art/candidates/${encodeURIComponent(jobId)}/report`; }

  getScript(projectId: string): Promise<ScriptReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/script`); }
  prepareScriptCandidate(projectId: string): Promise<ScriptCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/candidates`, { method: "POST" }); }
  recoverScriptHandoff(projectId: string, jobId: string): Promise<ScriptCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/candidates/${encodeURIComponent(jobId)}/handoff`); }
  refreshScriptCandidate(projectId: string, jobId: string): Promise<ScriptCandidate> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/candidates/${encodeURIComponent(jobId)}/refresh`, { method: "POST" }); }
  cancelScriptCandidate(projectId: string, jobId: string): Promise<ScriptReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/candidates/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }); }
  acceptScriptCandidate(projectId: string, body: { jobId: string; expectedScriptRevision: number; binding: unknown; script: Record<string, unknown> }): Promise<ScriptReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/accept`, { method: "POST", body: JSON.stringify(body) }); }
  reopenScript(projectId: string, expectedScriptRevision: number): Promise<ScriptReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/reopen`, { method: "POST", body: JSON.stringify({ expectedScriptRevision }) }); }
  saveScriptSection(projectId: string, body: { expectedScriptRevision: number; binding: unknown; sectionId: string; episode: Record<string, unknown> }): Promise<ScriptReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/script/sections/save`, { method: "POST", body: JSON.stringify(body) }); }
  scriptCandidateReportUrl(projectId: string, jobId: string): string { return `${this.base}/projects/${encodeURIComponent(projectId)}/script/candidates/${encodeURIComponent(jobId)}/report`; }

  getStoryboardSourceReview(projectId: string): Promise<StoryboardReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review`); }
  prepareStoryboardSourceReviewCandidate(projectId: string): Promise<StoryboardReviewCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review/candidates`, { method: "POST" }); }
  recoverStoryboardSourceReviewHandoff(projectId: string, jobId: string): Promise<StoryboardReviewCandidatePreparation> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review/candidates/${encodeURIComponent(jobId)}/handoff`); }
  refreshStoryboardSourceReviewCandidate(projectId: string, jobId: string): Promise<StoryboardReviewCandidate> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review/candidates/${encodeURIComponent(jobId)}/refresh`, { method: "POST" }); }
  cancelStoryboardSourceReviewCandidate(projectId: string, jobId: string): Promise<StoryboardReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review/candidates/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }); }
  acceptStoryboardSourceReviewCandidate(projectId: string, body: { jobId: string; expectedReviewRevision: number; binding: unknown }): Promise<StoryboardReviewState> { return this.request(`/projects/${encodeURIComponent(projectId)}/storyboard-source-review/accept`, { method: "POST", body: JSON.stringify(body) }); }
  storyboardSourceReviewCandidateReportUrl(projectId: string, jobId: string): string { return `${this.base}/projects/${encodeURIComponent(projectId)}/storyboard-source-review/candidates/${encodeURIComponent(jobId)}/report`; }

  getVideoPilotBudget(): Promise<VideoPilotBudget> { return this.request("/video-pilot-budget"); }
  getVideoBackend(): Promise<VideoBackend> { return this.request("/video-backend"); }
  getVideoJobs(projectId: string): Promise<{ jobs: VideoJob[] }> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs`); }
  prepareVideoJob(projectId: string, body: {
    approvalId: string; shotId: string; storyboardRevision: number; expectedSelectionRevision: number; idempotencyKey: string;
    requestedDurationSeconds?: number; resolution?: string; audio?: true;
    aspectPolicy?: "cover_center_crop" | "contain_pad" | "reject_mismatch";
    allowLetterbox?: boolean; allowCenterCrop?: boolean; seed?: number; profileId?: string;
  }): Promise<VideoJob> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs`, { method: "POST", body: JSON.stringify(body) });
  }
  submitVideoJob(projectId: string, id: string): Promise<VideoJob> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/submit`, { method: "POST" }); }
  reconcileVideoJob(projectId: string, id: string): Promise<VideoJob> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/reconcile`, { method: "POST" }); }
  cancelVideoJob(projectId: string, id: string): Promise<VideoJob> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }); }
  reviewVideoJob(projectId: string, id: string, decision: "select" | "reject", reviewer: string, note: string, expectedSelectionRevision: number): Promise<unknown> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify({ decision, reviewer, note, expectedSelectionRevision }) }); }
  discardVideoJob(projectId: string, id: string, expectedSelectionRevision: number): Promise<void> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/discard`, { method: "POST", body: JSON.stringify({ expectedSelectionRevision }) }); }
  discardUnselectedVideoJobs(projectId: string, shotId: string, videoJobIds: string[], expectedSelectionRevision: number): Promise<void> { return this.request(`/projects/${encodeURIComponent(projectId)}/video-jobs/discard-unselected`, { method: "POST", body: JSON.stringify({ shotId, videoJobIds, expectedSelectionRevision }) }); }
  videoJobMediaUrl(projectId: string, id: string): string { return `${this.base}/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(id)}/media`; }

  getProviderSettings(): Promise<ProviderSettings> {
    return this.request("/provider-settings");
  }

  putProviderSettings(settings: ProviderSettings | ProviderSettingsUpdate): Promise<ProviderSettings> {
    const update: ProviderSettingsUpdate = {
      expectedProfileId: "profileId" in settings ? settings.profileId : settings.expectedProfileId,
      expectedRevision: "revision" in settings ? settings.revision : settings.expectedRevision,
    };
    const publicKeys = [
      "textProvider", "textBaseUrl", "textModel", "textAuthMode", "textCapabilities",
      "textContextWindowTokens", "textMaxOutputTokens", "textTemperature", "textMaxConcurrency",
      "textConnectTimeoutSeconds", "textAttemptTimeoutSeconds",
      "imageProvider", "imageBaseUrl", "imageModel", "imageAuthMode",
      "videoProvider", "videoBaseUrl", "videoModel", "videoAuthMode",
    ] as const;
    for (const key of publicKeys) {
      if (key in settings) (update as Record<string, unknown>)[key] = settings[key];
    }
    return this.request("/provider-settings", { method: "PUT", body: JSON.stringify(update) });
  }

  getTextProviderProfiles(signal?: AbortSignal): Promise<TextProviderProfilesResponse> {
    return this.request("/text-provider-profiles", { signal });
  }

  createTextProviderProfile(body: TextProviderProfileCreate): Promise<TextProviderProfileView> {
    return this.request("/text-provider-profiles", { method: "POST", body: JSON.stringify(body) });
  }

  updateTextProviderProfile(profileId: string, expectedRevision: number, displayName: string, configuration: TextProviderProfileConfiguration, adapterId: string, adapterVersion: string): Promise<TextProviderProfileView> {
    return this.request(`/text-provider-profiles/${encodeURIComponent(profileId)}`, {
      method: "PUT",
      body: JSON.stringify({ expectedRevision, displayName, configuration, adapterId, adapterVersion }),
    });
  }

  deleteTextProviderProfile(profileId: string, expectedRevision: number): Promise<void> {
    return this.request(`/text-provider-profiles/${encodeURIComponent(profileId)}?expectedRevision=${encodeURIComponent(String(expectedRevision))}`, { method: "DELETE" });
  }

  activateTextProviderProfile(profileId: string, expectedSelectionRevision: number): Promise<TextProviderProfileSelection> {
    return this.request(`/text-provider-profiles/${encodeURIComponent(profileId)}/activate`, {
      method: "POST",
      body: JSON.stringify({ expectedSelectionRevision }),
    });
  }

  setTextProviderProfileAvailability(profileId: string, expectedAvailabilityRevision: number, enabled: boolean): Promise<TextProviderProfileView> {
    return this.request(`/text-provider-profiles/${encodeURIComponent(profileId)}/availability`, {
      method: "PUT",
      body: JSON.stringify({ expectedAvailabilityRevision, enabled }),
    });
  }

  probeTextProviderProfile(profileId: string, includeSessionKey = true): Promise<TextProviderProfileProbe> {
    return this.request(`/text-provider-profiles/${encodeURIComponent(profileId)}/probe`, { method: "POST" }, includeSessionKey, profileId);
  }
}

export const plotloomApi = new PlotloomApiClient();
