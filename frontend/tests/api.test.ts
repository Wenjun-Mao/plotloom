import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlotloomApiClient } from "../src/api";
import { providerSessionKey, providerSessionKeys } from "../src/session-key";

describe("PlotloomApiClient", () => {
  beforeEach(() => { window.sessionStorage.clear(); window.localStorage.clear(); });

  it("invokes a browser fetch implementation with the platform global receiver", async () => {
    const fetcher = vi.fn(function (this: unknown) {
      if (this !== globalThis) throw new TypeError("Illegal invocation");
      return Promise.resolve(new Response(JSON.stringify({ id: "p1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }));
    });
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await expect(client.getProject("p1")).resolves.toEqual({ id: "p1" });
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("sends expectedRevision and the canonical stage endpoint", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ stage: "story_graph", revision: 8, status: "ready" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.patchStage("project/a b", "story_graph", 7, { startNodeId: "n1", nodes: [], edges: [], joinContracts: [] });

    expect(fetcher).toHaveBeenCalledOnce();
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v2/projects/project%2Fa%20b/stages/story_graph");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toMatchObject({ expectedRevision: 7, payload: { startNodeId: "n1" } });
  });

  it("uses lifecycle revisions and an explicit title confirmation for project lifecycle actions", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "p1" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.archiveProject("p1", 4);
    await client.restoreProject("p1", 5);
    await client.duplicateProject("p1", 6, undefined, "duplicate-key");
    await client.permanentlyDeleteProject("p1", 7, "Moon City");

    const calls = fetcher.mock.calls as unknown as Array<[string, RequestInit]>;
    expect(calls.map(([url]) => url)).toEqual([
      "/api/v2/projects/p1/archive", "/api/v2/projects/p1/restore",
      "/api/v2/projects/p1/duplicate", "/api/v2/projects/p1/permanent-delete",
    ]);
    expect(JSON.parse(String(calls[0][1].body))).toEqual({ expectedLifecycleRevision: 4 });
    expect(new Headers(calls[2][1].headers).get("Idempotency-Key")).toBe("duplicate-key");
    expect(JSON.parse(String(calls[3][1].body))).toEqual({ expectedLifecycleRevision: 7, confirmationTitle: "Moon City" });
  });

  it("creates and reads a server-owned snapshot without sending a browser path", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      operationId: "snapshot-1", snapshotId: "snapshot-1", projectId: "p1", status: "complete",
      location: "/application/outputs/.snapshots/p1/snapshot-1", manifest: { files: [] },
    }), { status: 201, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.createProjectSnapshot("p1");
    await client.getProjectSnapshot("p1", "snapshot/1");

    const calls = fetcher.mock.calls as unknown as Array<[string, RequestInit]>;
    expect(calls[0][0]).toBe("/api/v2/projects/p1/snapshots");
    expect(calls[0][1].method).toBe("POST");
    expect(calls[0][1].body).toBeUndefined();
    expect(calls[1][0]).toBe("/api/v2/projects/p1/snapshots/snapshot%2F1");
  });

  it("requests the lifecycle status query and unwraps no stale client-side filter", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ projects: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.listProjects();
    await client.listProjects(true);

    expect((fetcher.mock.calls[0] as unknown as [string])[0]).toBe("/api/v2/projects?status=active&limit=50");
    expect((fetcher.mock.calls[1] as unknown as [string])[0]).toBe("/api/v2/projects?status=all&limit=50");
  });

  it("passes a directory cursor without changing the selected lifecycle filter", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ projects: [], nextCursor: null }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.listProjects(true, 50, "after-project-50");

    expect((fetcher.mock.calls[0] as unknown as [string])[0]).toBe("/api/v2/projects?status=all&limit=50&cursor=after-project-50");
  });

  it("sends the canonical creation body and caller-owned idempotency key", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "p1", revision: 1, brief: {}, createdAt: "now", updatedAt: "now", stages: [] }), { status: 201, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);
    const request = {
      brief: { title: "first save" } as never,
      initialStages: [{ stage: "story_bible" as const, payload: { logline: "draft" } }],
    };

    await client.createProject(request, "first-save-key");

    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v2/projects");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Idempotency-Key")).toBe("first-save-key");
    expect(JSON.parse(String(init.body))).toEqual(request);
  });

  it("keeps the ephemeral provider key out of JSON and sends only the session header", async () => {
    providerSessionKey.write("  session-secret  ");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "run-1", status: "queued" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.startRun("p1", ["story_bible"]);

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("X-Plotloom-Session-API-Key")).toBe("session-secret");
    expect(String(init.body)).not.toContain("session-secret");
    expect(window.localStorage.length).toBe(0);
  });

  it("keeps separate profile keys in a session-only map and sends the selected profile key", async () => {
    providerSessionKeys.write("default", "default-secret");
    providerSessionKeys.write("quality", " quality-secret ");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "run-1", status: "queued" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.startRun("p1", ["story_bible"], "quality");

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).get("X-Plotloom-Session-API-Key")).toBe("quality-secret");
    expect(JSON.parse(String(init.body))).toEqual({ stages: ["story_bible"], providerProfileId: "quality" });
    expect(window.sessionStorage.getItem("plotloom:provider-session-keys")).toContain("quality-secret");
    expect(window.localStorage.length).toBe(0);
    expect(String(init.body)).not.toContain("quality-secret");
  });

  it("does not send a retained profile key when authMode is none", async () => {
    providerSessionKeys.write("anonymous", "stale-but-unneeded-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "run-1", status: "queued" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.startRun("p1", ["story_bible"], "anonymous", false);
    await client.probeTextProviderProfile("anonymous", false);

    for (const [, init] of fetcher.mock.calls as unknown as Array<[string, RequestInit]>) {
      expect(new Headers(init.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
      expect(String(init.body || "")).not.toContain("stale-but-unneeded-secret");
    }
    expect(providerSessionKeys.read("anonymous")).toBe("stale-but-unneeded-secret");
  });

  it("scopes rebuild and resume credentials to the explicit profile", async () => {
    providerSessionKeys.write("default", "default-secret");
    providerSessionKeys.write("quality", "quality-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "run-1", status: "queued" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.rebuild("p1", "story_graph", "quality");
    await client.resumeRun("run-1", "quality");

    const calls = fetcher.mock.calls as unknown as Array<[string, RequestInit]>;
    expect(JSON.parse(String(calls[0][1].body))).toEqual({ fromStage: "story_graph", providerProfileId: "quality" });
    expect(calls[1][0]).toBe("/api/v2/runs/run-1/resume");
    for (const [, init] of calls) {
      expect(new Headers(init.headers).get("X-Plotloom-Session-API-Key")).toBe("quality-secret");
      expect(String(init.body)).not.toContain("quality-secret");
      expect(String(init.body)).not.toContain("default-secret");
    }
  });

  it("uses a secret-free exact work-unit repair payload and the parent frozen profile key", async () => {
    providerSessionKeys.write("default", "default-secret");
    providerSessionKeys.write("frozen_quality", "quality-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "child-run", status: "queued" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.repairWorkUnit("parent/run", "unit/a b", "frozen_quality", "repair-key");

    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v2/runs/parent%2Frun/work-units/unit%2Fa%20b/repairs");
    expect(new Headers(init.headers).get("Idempotency-Key")).toBe("repair-key");
    expect(new Headers(init.headers).get("X-Plotloom-Session-API-Key")).toBe("quality-secret");
    expect(JSON.parse(String(init.body))).toEqual({});
    expect(String(init.body)).not.toContain("frozen_quality");
    expect(String(init.body)).not.toContain("quality-secret");
    expect(String(init.body)).not.toContain("default-secret");
  });

  it("reads only the lightweight run-progress endpoint during status polling", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      runId: "run-1", status: "running", failureCode: null, failedStage: null,
      stageProgress: [], workUnits: [], actions: { canResume: false, canCancel: true, canRebuildStage: false, repairEligible: false },
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    const progress = await client.getRunProgress("run/1");

    expect((fetcher.mock.calls[0] as unknown as [string])[0]).toBe("/api/v2/runs/run%2F1/progress");
    expect(progress).not.toHaveProperty("artifacts");
    expect(progress).not.toHaveProperty("attempts");
  });

  it("sends profile saves before probes without serializing the profile session key", async () => {
    providerSessionKeys.write("quality", "probe-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ profileId: "quality" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);
    const configuration = {
      profileSchemaVersion: 2 as const, profileId: "quality", profileVersion: 1, profileHash: "",
      textProvider: "openai-compatible", textBaseUrl: "https://example.test/v1", textModel: "model",
      textAuthMode: "bearer" as const, textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: false, chatTemplateKwargs: false },
      textContextWindowTokens: 32768, textMaxOutputTokens: 8192, textTemperature: 0.2, textMaxConcurrency: 1,
      textConnectTimeoutSeconds: 10, textAttemptTimeoutSeconds: 300, redirectPolicy: "no_follow" as const,
      requestExtension: "none" as const, reasoningMode: "provider_default" as const,
      extractionPolicy: { allowJsonFence: false, allowLeadingThinkBlock: false },
      stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 },
      maxSemanticCorrections: 2, presetId: "custom" as const, presetVersion: "1",
    };

    await client.updateTextProviderProfile("quality", 1, "Quality", configuration, "openai_compatible", "1");
    await client.probeTextProviderProfile("quality");

    const [, saveInit] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    const [, probeInit] = fetcher.mock.calls[1] as unknown as [string, RequestInit];
    expect(JSON.parse(String(saveInit.body))).toEqual({ expectedRevision: 1, displayName: "Quality", configuration, adapterId: "openai_compatible", adapterVersion: "1" });
    expect(String(saveInit.body)).not.toContain("probe-secret");
    expect(new Headers(saveInit.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
    expect(new Headers(probeInit.headers).get("X-Plotloom-Session-API-Key")).toBe("probe-secret");
  });

  it("does not echo read-only provider profile or key availability fields in PUT", async () => {
    providerSessionKey.write("must-not-leave-on-settings-request");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ revision: 3, textKeyAvailable: true }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    const settingsWithReadOnlyFields = {
      expectedProfileId: "default", expectedRevision: 2, textModel: "model-a",
      profileId: "default", profileVersion: 2, profileHash: "public-only-hash", revision: 2,
      textKeyAvailable: true, imageKeyAvailable: false, videoKeyAvailable: false,
    };
    await client.putProviderSettings(settingsWithReadOnlyFields);

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
    expect(JSON.parse(String(init.body))).toEqual({
      expectedProfileId: "default",
      expectedRevision: 2,
      textModel: "model-a",
    });
  });

  it("sends no session credential on reads or canonical project writes", async () => {
    providerSessionKey.write("must-not-leave-on-non-provider-request");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.getProject("p1");
    await client.getTrace("run-1");

    for (const [, init] of fetcher.mock.calls as unknown as Array<[string, RequestInit]>) {
      expect(new Headers(init.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
    }
  });

  it("keeps the legacy media request secret-free and accepts no client media inputs", async () => {
    providerSessionKey.write("text-profile-session-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "media-1", shotId: "shot-1", kind: "video", status: "queued" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.startMediaTask("p1", "shot-1", "video");

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
    expect(JSON.parse(String(init.body))).toEqual({
      kind: "video",
    });
  });
});
