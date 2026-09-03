import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlotloomApiClient } from "../src/api";
import { providerSessionKey } from "../src/session-key";

describe("PlotloomApiClient", () => {
  beforeEach(() => window.sessionStorage.clear());

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

  it("does not echo read-only provider profile or key availability fields in PUT", async () => {
    providerSessionKey.write("must-not-leave-on-settings-request");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ revision: 3, textKeyAvailable: true }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.putProviderSettings({ textModel: "model-a", profileId: "default", profileVersion: 2, profileHash: "public-only-hash", revision: 2, textKeyAvailable: true, imageKeyAvailable: false, videoKeyAvailable: false });

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
    expect(JSON.parse(String(init.body))).toEqual({ textModel: "model-a" });
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

  it("sends a successful keyframe URI as public video-task input", async () => {
    providerSessionKey.write("media-session-secret");
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ id: "media-1", shotId: "shot-1", kind: "video", status: "queued" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);

    await client.startMediaTask("p1", "shot-1", "video", { sourceUri: "https://assets.example/keyframe.png" });

    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).get("X-Plotloom-Session-API-Key")).toBe("media-session-secret");
    expect(JSON.parse(String(init.body))).toEqual({
      kind: "video",
      publicSettings: { sourceUri: "https://assets.example/keyframe.png" },
    });
  });
});
