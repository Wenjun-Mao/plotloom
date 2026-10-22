// @vitest-environment node
import { createServer, type RequestListener, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, expect, it, vi } from "vitest";
import { pollHttpReadiness } from "../e2e/http-readiness";

let server: Server | undefined;
const ownedProcess = (exitCode: number | null = null) => ({ child: { exitCode }, label: "Owned Vite", output: () => "preserved startup output" });
async function listen(handler: RequestListener): Promise<string> {
  server = createServer(handler);
  await new Promise<void>(resolve => server!.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}/ready`;
}
afterEach(async () => {
  vi.useRealTimers(); vi.restoreAllMocks();
  if (!server) return;
  server.closeAllConnections();
  await new Promise<void>((resolve, reject) => server!.close(error => error ? reject(error) : resolve()));
  server = undefined;
});

it("admits an actual successful HTTP response", async () => {
  const url = await listen((_request, response) => { response.writeHead(200); response.end("ready"); });
  await expect(pollHttpReadiness(url, ownedProcess(), Date.now() + 1000)).resolves.toBeUndefined();
});

it("aborts a socket that never responds and reports the exact owner output", async () => {
  const url = await listen(() => { /* Intentionally accept without responding. */ });
  const started = Date.now();
  await expect(pollHttpReadiness(url, ownedProcess(), started + 100)).rejects.toThrow(`Owned Vite did not become ready at ${url}`);
  expect(Date.now() - started).toBeLessThan(1000);
  await expect(pollHttpReadiness(url, ownedProcess(), Date.now() + 50)).rejects.toThrow("preserved startup output");
});

it("retains a non-success status and process-exit diagnostics", async () => {
  const url = "http://127.0.0.1:1/ready";
  vi.useFakeTimers();
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("not ready", { status: 503, statusText: "Service Unavailable" }));
  const failure = expect(pollHttpReadiness(url, ownedProcess(), Date.now() + 100)).rejects.toThrow("last HTTP response: 503 Service Unavailable");
  await vi.advanceTimersByTimeAsync(100); await failure;
  await expect(pollHttpReadiness(url, ownedProcess(1), Date.now() + 100)).rejects.toThrow("code 1).\npreserved startup output");
});
