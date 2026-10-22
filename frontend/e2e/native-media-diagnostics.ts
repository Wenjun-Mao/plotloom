import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import type { CDPSession, ConsoleMessage, Page, Response, TestInfo } from "@playwright/test";

type TraceReader = "readBranchingMediaTrace" | "readNativeTrace";
type DiagnosticSource = { responseUrl: RegExp; traceReader: TraceReader };

/** Read-only evidence collected before teardown, including early playback failures. */
export async function collectNativeMediaDiagnostics(page: Page, info: TestInfo, source: DiagnosticSource) {
  const events: Array<{ type: string; payload: unknown }> = [];
  const responses: Array<{ url: string; status: number; headers: Record<string, string>; bytes?: Buffer; bodyState: "pending" | "complete" | "failed"; error?: string }> = [];
  const pendingReads: Promise<void>[] = [];
  const cdp: CDPSession = await page.context().newCDPSession(page);
  for (const type of ["playerCreated", "playerPropertiesChanged", "playerEventsAdded", "playerMessagesLogged", "playerErrorsRaised"] as const) {
    cdp.on(`Media.${type}`, payload => events.push({ type, payload }));
  }
  await cdp.send("Media.enable");
  const onConsole = (message: ConsoleMessage) => {
    if (message.type() === "error" || message.type() === "warning") events.push({ type: `console-${message.type()}`, payload: message.text() });
  };
  const onPageError = (error: Error) => { events.push({ type: "pageerror", payload: error.message }); };
  const onResponse = (response: Response) => {
    if (!source.responseUrl.test(response.url())) return;
    const entry: typeof responses[number] = { url: response.url(), status: response.status(), headers: response.headers(), bodyState: "pending" };
    responses.push(entry);
    pendingReads.push((async () => {
      try {
        entry.bytes = await response.body(); entry.bodyState = "complete";
      } catch (error) {
        entry.bodyState = "failed"; entry.error = String(error);
      }
    })());
  };
  page.on("console", onConsole); page.on("pageerror", onPageError); page.on("response", onResponse);
  return async () => {
    // Preserve state immediately. A stalled response body must not consume
    // teardown or erase the very evidence needed to diagnose that stall.
    try {
      const snapshot = await boundedDiagnostic<unknown>(page.evaluate((traceReader: TraceReader) => ({
        trace: (window as typeof window & Partial<Record<TraceReader, () => unknown[]>>)[traceReader]?.() ?? [],
        videos: [...document.querySelectorAll("video")].map(video => ({
          src: video.currentSrc, connected: video.isConnected, identity: video.dataset.playbackIdentity,
          currentTime: video.currentTime, duration: video.duration, paused: video.paused, ended: video.ended,
          readyState: video.readyState, networkState: video.networkState,
          error: video.error ? { code: video.error.code, message: video.error.message } : null,
          buffered: Array.from({ length: video.buffered.length }, (_, index) => [video.buffered.start(index), video.buffered.end(index)]),
          frames: video.getVideoPlaybackQuality().totalVideoFrames,
        })),
      }), source.traceReader).catch(error => ({ unavailable: String(error) })), { unavailable: "renderer snapshot did not settle within the diagnostic budget" });
      await boundedDiagnostic(Promise.allSettled(pendingReads), []);
      const evidencePath = info.outputPath("native-media-diagnostics.json");
      await writeFile(evidencePath, JSON.stringify({
        snapshot, events,
        responses: responses.map(({ bytes, ...metadata }) => ({ ...metadata,
          byteCount: bytes?.length ?? null, sha256: bytes ? createHash("sha256").update(bytes).digest("hex") : null })),
      }, null, 2));
      await info.attach("native-media-diagnostics", { contentType: "application/json", path: evidencePath });
      if (info.status !== info.expectedStatus) {
        for (const [index, response] of responses.entries()) {
          if (response.bytes) {
            const range = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers["content-range"] ?? "");
            const wholeObject = response.status === 200 || (response.status === 206 && range
              && Number(range[1]) === 0 && Number(range[2]) + 1 === Number(range[3]) && response.bytes.length === Number(range[3]));
            const suffix = wholeObject ? ".mp4" : response.status === 206 ? "-range-data.bin" : "-response-data.bin";
            const mediaPath = info.outputPath(`native-playback-response-${index}${suffix}`);
            await writeFile(mediaPath, response.bytes);
            await info.attach(`native-playback-response-${index}`, { path: mediaPath, contentType: wholeObject ? "video/mp4" : "application/octet-stream" });
          }
        }
      }
    } finally {
      page.off("console", onConsole); page.off("pageerror", onPageError); page.off("response", onResponse);
      await boundedDiagnostic(cdp.detach().catch(() => {}), undefined);
    }
  };
}

/** This budget limits evidence collection only, never gameplay acceptance. */
async function boundedDiagnostic<T>(promise: Promise<T>, unavailable: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try { return await Promise.race([promise, new Promise<T>(resolve => { timer = setTimeout(() => resolve(unavailable), 1000); })]); }
  finally { if (timer) clearTimeout(timer); }
}
