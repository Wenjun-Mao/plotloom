import { afterEach, expect, it, vi } from "vitest";
import { PlotloomApiClient, ApiError } from "../src/api";
import { ProjectReadAdmission } from "../src/project-read-admission";
import { messageFrom } from "../src/app/workspace/contracts";

afterEach(() => vi.useRealTimers());

function heldBody() {
  let body!: ReadableStreamDefaultController<Uint8Array>;
  const response = new Response(new ReadableStream({ start(controller) { body = controller; } }), { headers: { "Content-Type": "application/json" } });
  return { response, finish: () => { body.enqueue(new TextEncoder().encode("{}")); body.close(); } };
}

it("settles project and collection bodies, queues new same-project reads, and allows other projects and draft writes", async () => {
  const project = heldBody(), collection = heldBody();
  const projectResponses = [project.response], collectionResponses = [collection.response];
  const fetcher = vi.fn(async (url: unknown) =>
    (String(url).endsWith("/script") ? projectResponses.shift() : String(url).includes("/projects?") ? collectionResponses.shift() : undefined) ?? new Response("{}"));
  const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);
  const script = client.getScript("p"), directory = client.listProjects();
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  const reads = client.suspendProjectReads("p");
  let settled = false;
  const settling = reads.settle().then(result => { settled = result; });
  const queued = client.getProject("p"), nextDirectory = client.listProjects();
  await client.getProject("other");
  await client.saveAuthoringDraft("p", { editorScope: "story_graph", entityId: "root", baseCanonicalRevision: 0, expectedDraftRevision: 0, payload: {} });
  expect(fetcher).toHaveBeenCalledTimes(4); expect(settled).toBe(false);
  project.finish(); await script; expect(settled).toBe(false);
  collection.finish(); await directory; await settling; expect(settled).toBe(true);
  reads.resume(); reads.resume();
  await Promise.all([queued, nextDirectory]); expect(fetcher).toHaveBeenCalledTimes(6);
});

it("tracks full report-probe bodies and independent document tickets", async () => {
  const body = heldBody();
  const client = new PlotloomApiClient(vi.fn(async () => body.response) as unknown as typeof fetch);
  const url = "/api/v2/projects/p/source-outline/candidates/c/report";
  const probe = client.reportAvailable(url, new AbortController().signal);
  const frame = await client.admitReportRead(url, new AbortController().signal);
  const paused = client.suspendProjectReads("p"); let done = false;
  const settling = paused.settle().then(result => { done = result; });
  body.finish(); await probe; expect(done).toBe(false);
  frame.complete(); await settling; expect(done).toBe(true); paused.resume();
});

it("does not swallow an aborted JSON body or infer the server lease completed", async () => {
  let body!: ReadableStreamDefaultController<Uint8Array>;
  const fetcher = vi.fn(async (_: unknown, init?: RequestInit) => {
    const stream = new ReadableStream<Uint8Array>({ start(controller) { body = controller; } });
    init?.signal?.addEventListener("abort", () => body.error(init.signal!.reason), { once: true });
    return new Response(stream);
  });
  const client = new PlotloomApiClient(fetcher as unknown as typeof fetch), controller = new AbortController();
  const read = client.getProject("p", controller.signal);
  const rejected = expect(read).rejects.toMatchObject({ name: "AbortError" });
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
  const pause = client.suspendProjectReads("p"), settling = pause.settle();
  controller.abort(); await rejected; await expect(settling).resolves.toBe(false); pause.resume();
});

it("cancels queued admission promptly and treats live frame cleanup as unknown, then resumes after failure", async () => {
  const reads = new ProjectReadAdmission();
  const live = await reads.acquire("p");
  const paused = reads.suspend("p"), controller = new AbortController();
  const queued = reads.acquire("p", controller.signal);
  const rejection = expect(queued).rejects.toMatchObject({ name: "AbortError" });
  controller.abort(); await rejection;
  const settling = paused.settle(); live.cancel(); live.complete();
  await expect(settling).resolves.toBe(false);
  paused.resume();
  const next = await reads.acquire("p"), second = reads.suspend("p");
  live.complete();
  let done = false; const wait = second.settle().then(result => { done = result; });
  await Promise.resolve(); expect(done).toBe(false);
  next.complete(); await wait; expect(done).toBe(true); second.resume();
});

it("fails closed on an unsettled document deadline and releases admission without claiming server completion", async () => {
  vi.useFakeTimers();
  const reads = new ProjectReadAdmission(), live = await reads.acquire("p");
  const paused = reads.suspend("p"), settling = paused.settle();
  await vi.advanceTimersByTimeAsync(30_000); await expect(settling).resolves.toBe(false);
  paused.resume(); live.cancel();
  const next = await reads.acquire("p"); next.complete();
});

it("classifies only explicit revision conflicts and preserves busy/other409 meaning", () => {
  expect(messageFrom(new ApiError("busy", 409, { code: "project_busy" }))).toContain("占用");
  expect(messageFrom(new ApiError("busy", 409, { code: "project_busy" }))).not.toContain("版本冲突");
  expect(messageFrom(new ApiError("CAS", 409, { code: "revision_conflict" }))).toContain("版本冲突");
  expect(messageFrom(new ApiError("currentness", 409, { code: "stale_binding" }))).toBe("currentness");
});

it("settles a complete HTTP refusal but not a truncated response body", async () => {
  let finish!: (response: Response) => void;
  const client = new PlotloomApiClient(vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })) as typeof fetch);
  const request = client.getProject("p");
  const rejection = expect(request).rejects.toMatchObject({ status: 409 });
  await vi.waitFor(() => expect(finish).toBeTypeOf("function"));
  const pause = client.suspendProjectReads("p");
  try {
    const settling = pause.settle();
    finish(new Response('{"code":"project_busy"}', { status: 409 }));
    await rejection; await expect(settling).resolves.toBe(true);
  } finally { pause.resume(); }

  let body!: ReadableStreamDefaultController<Uint8Array>;
  const response = new Response(new ReadableStream({ start(controller) { body = controller; } }));
  const interrupted = new PlotloomApiClient(vi.fn(async () => response) as typeof fetch);
  const read = interrupted.getProject("p");
  const failure = expect(read).rejects.toThrow("stream interrupted");
  const held = interrupted.suspendProjectReads("p");
  try {
    const settling = held.settle();
    body.error(new TypeError("stream interrupted"));
    await failure; await expect(settling).resolves.toBe(false);
  } finally { held.resume(); }
});
