import type {
  MediaKind,
  MediaTask,
  ProjectCreationRequest,
  ProjectCreationResponse,
  PipelineRun,
  ProjectBrief,
  ProjectMediaTasksResponse,
  ProjectResource,
  ProjectRunsResponse,
  ProviderSettings,
  ProviderSettingsUpdate,
  ServerStageName,
  StageEnvelopesResponse,
  StageHead,
  RunTrace,
} from "./types";
import { providerSessionKey } from "./session-key";
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
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body) headers.set("Content-Type", "application/json");
    if (includeSessionKey) {
      const ephemeralKey = providerSessionKey.read();
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

  getProject(projectId: string): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}`);
  }

  patchProject(projectId: string, expectedRevision: number, brief: ProjectBrief): Promise<ProjectResource> {
    return this.request(`/projects/${encodeURIComponent(projectId)}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, brief }),
    });
  }

  getStages(projectId: string): Promise<StageEnvelopesResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/stages`);
  }

  getProjectRuns(projectId: string): Promise<ProjectRunsResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/runs`);
  }

  getProjectMediaTasks(projectId: string): Promise<ProjectMediaTasksResponse> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/media-tasks`);
  }

  patchStage<T>(projectId: string, stage: ServerStageName, expectedRevision: number, content: T): Promise<StageHead> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/stages/${stage}`, {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision, payload: content }),
    });
  }

  startRun(projectId: string, stages: ServerStageName[]): Promise<PipelineRun> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/pipeline-runs`, {
      method: "POST",
      body: JSON.stringify({ stages }),
    }, true);
  }

  rebuild(projectId: string, fromStage: ServerStageName): Promise<PipelineRun> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/rebuilds`, {
      method: "POST",
      body: JSON.stringify({ fromStage }),
    }, true);
  }

  getRun(runId: string): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}`);
  }

  getTrace(runId: string): Promise<RunTrace> {
    return this.request(`/runs/${encodeURIComponent(runId)}/trace`);
  }

  cancelRun(runId: string): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST", body: "{}" });
  }

  repairRun(runId: string, stage: ServerStageName, instructions: string): Promise<PipelineRun> {
    return this.request(`/runs/${encodeURIComponent(runId)}/repairs`, {
      method: "POST",
      body: JSON.stringify({ stage, instructions }),
    }, true);
  }

  startMediaTask(projectId: string, shotId: string, kind: MediaKind, publicSettings?: Record<string, unknown>): Promise<MediaTask> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/shots/${encodeURIComponent(shotId)}/media-tasks`, {
      method: "POST",
      body: JSON.stringify({ kind, ...(publicSettings ? { publicSettings } : {}) }),
    }, true);
  }

  getMediaTask(taskId: string): Promise<MediaTask> {
    return this.request(`/media-tasks/${encodeURIComponent(taskId)}`);
  }

  getProviderSettings(): Promise<ProviderSettings> {
    return this.request("/provider-settings");
  }

  putProviderSettings(settings: ProviderSettings | ProviderSettingsUpdate): Promise<ProviderSettings> {
    const update: ProviderSettingsUpdate = {};
    const publicKeys: (keyof ProviderSettingsUpdate)[] = [
      "textProvider", "textBaseUrl", "textModel", "textAuthMode", "textCapabilities",
      "textContextWindowTokens", "textMaxOutputTokens", "textTemperature", "textMaxConcurrency",
      "textConnectTimeoutSeconds", "textAttemptTimeoutSeconds",
      "imageProvider", "imageBaseUrl", "imageModel", "imageAuthMode",
      "videoProvider", "videoBaseUrl", "videoModel", "videoAuthMode",
    ];
    for (const key of publicKeys) {
      if (key in settings) (update as Record<string, unknown>)[key] = settings[key];
    }
    return this.request("/provider-settings", { method: "PUT", body: JSON.stringify(update) });
  }
}

export const plotloomApi = new PlotloomApiClient();
