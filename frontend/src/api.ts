import type {
  MediaKind,
  MediaTask,
  ProjectCreationRequest,
  ProjectCreationResponse,
  ProjectDuplicateResponse,
  PipelineRun,
  ProjectBrief,
  ProjectMediaTasksResponse,
  ProjectListResponse,
  ProjectResource,
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
  StillPreview,
  VisualWorkbench,
  VisualIntent,
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
    approvalId: string; shotId: string; storyboardRevision: number; parentCandidateAssetId?: string; presentationChange: string;
  }): Promise<{ job: ImageJob }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs`, { method: "POST", body: JSON.stringify(body) });
  }

  copyImageJob(projectId: string, jobId: string): Promise<{ job: ImageJob; assignment: string; packagePath: string; deliveryPath: string }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/copy`, { method: "POST" });
  }

  refreshImageJob(projectId: string, jobId: string): Promise<{ state: string; candidates: Array<{ assetId: string }> }> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/refresh`, { method: "POST" });
  }

  cancelImageJob(projectId: string, jobId: string, reason: string): Promise<ImageJob> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/image-jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
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

  repairRun(
    runId: string,
    stage: ServerStageName,
    instructions: string,
    providerProfileId = "default",
    includeSessionKey = true,
  ): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}/repairs`, {
      method: "POST",
      body: JSON.stringify({ stage, instructions, providerProfileId }),
    }, includeSessionKey, providerProfileId);
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
