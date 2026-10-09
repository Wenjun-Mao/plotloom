import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { specialistsApi, SpecialistApiError } from "../src/features/specialists/api";

afterEach(() => vi.unstubAllGlobals());

it("includes specialist bodies and queued image previews in the workspace lifecycle barrier", async () => {
  let body!: ReadableStreamDefaultController<Uint8Array>;
  const held = new Response(new ReadableStream({ start(controller) { body = controller; } }));
  const fetcher = vi.fn(async () => new Response("{}"));
  fetcher.mockResolvedValueOnce(held);
  vi.stubGlobal("fetch", fetcher);
  const status = specialistsApi.status("p", "storyboard", "job");
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
  const pause = plotloomApi.suspendProjectReads("p");
  try {
    let settled = false;
    const settling = pause.settle().then(result => { settled = result; });
    const queued = specialistsApi.imageTerminalPreview("p", "image_job", "image");
    await specialistsApi.status("other", "characters", "job");
    // Dispatch remains a mutation, not an automatically retried read.
    await specialistsApi.check("other", "characters", "job");
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(settled).toBe(false);
    body.enqueue(new TextEncoder().encode('{"state":"prepared"}')); body.close();
    await status; await settling;
    expect(settled).toBe(true);
    expect(fetcher).toHaveBeenCalledTimes(3);
    pause.resume(); await queued;
    expect(fetcher).toHaveBeenCalledTimes(4);
  } finally { pause.resume(); }
});

it("keeps specialist error details while settling fully received domain refusals", async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const pending = specialistsApi.status("p", "characters", "job");
  const rejected = expect(pending).rejects.toMatchObject({ status: 409, code: "stale_binding", message: "changed" });
  await vi.waitFor(() => expect(finish).toBeTypeOf("function"));
  const pause = plotloomApi.suspendProjectReads("p");
  try {
    const settling = pause.settle();
    finish(new Response(JSON.stringify({ detail: { code: "stale_binding", message: "changed" } }), { status: 409 }));
    await rejected; await expect(settling).resolves.toBe(true);
  } finally { pause.resume(); }
  vi.stubGlobal("fetch", vi.fn(async () => new Response("null")));
  await expect(specialistsApi.status("p", "characters", "job")).rejects.toBeInstanceOf(SpecialistApiError);
});

it("fails lifecycle settlement closed on interrupted specialist transport", async () => {
  let fail!: (error: Error) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((_, reject) => { fail = reject; })));
  const pending = specialistsApi.status("p", "characters", "job");
  const rejected = expect(pending).rejects.toThrow("interrupted");
  await vi.waitFor(() => expect(fail).toBeTypeOf("function"));
  const pause = plotloomApi.suspendProjectReads("p");
  try {
    const settling = pause.settle();
    fail(new TypeError("interrupted"));
    await rejected; await expect(settling).resolves.toBe(false);
  } finally { pause.resume(); }
});
