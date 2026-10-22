import { expect, it, vi } from "vitest";
import { PlotloomApiClient } from "../src/api";
import { bridgeState, prepareRequest } from "./production-bridge-fixture";

it("sends the complete server-qualified source/CAS/replacement body without reconstruction", async () => {
  const request = prepareRequest({ expectedProposalRevision: 8, expectedProposalContentHash: "c".repeat(64) });
  request.replacementTarget.installedAdmissionId = "the-current-installation";
  request.replacementTarget.storyboard = { revision: 5, entityRevisionId: "current-board", contentHash: "d".repeat(64), status: "ready" };
  const fetcher = vi.fn(async (_url: unknown, _init?: RequestInit) => new Response(JSON.stringify(bridgeState()), { status: 200 }));
  const client = new PlotloomApiClient(fetcher as unknown as typeof fetch);
  await client.prepareProductionBridge("project/a b", request);
  const [url, init] = fetcher.mock.calls[0];
  expect(url).toBe("/api/v2/projects/project%2Fa%20b/production-bridge/proposals");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual(request);
  expect(new Headers(init?.headers).has("X-Plotloom-Session-API-Key")).toBe(false);
});
