import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { autopilotApi } from "../src/features/autopilot/api";
import { plotloomApi } from "../src/api";
import { useDeliveryEvidence } from "../src/features/autopilot/useDeliveryEvidence";
import { deliveryDisclosure } from "../src/features/autopilot/deliveryEvidence";
import { evidenceReadsFixture } from "./autopilot-delivery-fixture";
import type { EvidenceReads } from "../src/features/autopilot/deliveryEvidence";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
function mockReads() {
  const assets = vi.spyOn(autopilotApi, "deliveryEvidence").mockImplementation(async id => evidenceReadsFixture(id));
  return assets;
}
async function harness() {
  const host = document.createElement("div"), root = createRoot(host);
  let reader!: ReturnType<typeof useDeliveryEvidence>;
  function Probe({ id, hash }: { id: string; hash: string }) {
    reader = useDeliveryEvidence(id, hash);
    const state = reader.state;
    const value = state?.status === "ready" ? deliveryDisclosure(id, { assetId: "hero-side", originalHash: "b".repeat(64) }, state.value) : null;
    return createElement("p", null, state?.status || "unknown", value?.status === "delivered" ? value.current.limitations.join("\n") : "");
  }
  return { host, get reader() { return reader; },
    render: (id: string, hash = "bundle") => act(async () => root.render(createElement(Probe, { id, hash }))),
    unmount: () => act(async () => root.unmount()) };
}

it("aborts old project/bundle reads and cannot display their late declarations", async () => {
  const assets = mockReads();
  let release!: (value: EvidenceReads) => void;
  assets.mockImplementationOnce(() => new Promise(done => { release = done; }));
  const state = await harness();
  try {
    await state.render("old"); expect(state.host.textContent).toBe("unknown");
    const signal = assets.mock.calls[0][1]!;
    await state.render("current"); expect(signal.aborted).toBe(true);
    expect(state.reader.state?.status).toBe("ready");
    await act(async () => release(evidenceReadsFixture("old")));
    const ready = state.reader.state!;
    if (ready.status !== "ready") throw new Error("current read should stay ready");
    expect(ready.value.assets.every(asset => asset.projectId === "current")).toBe(true);
    expect(state.host.textContent).toContain("补充参考");
  } finally { await state.unmount(); }
});

it("a failed evidence read stays unknown and explicit retry reads the same bundle without mutations", async () => {
  const assets = mockReads(); assets.mockRejectedValueOnce(new Error("evidence temporarily unavailable"));
  const write = vi.spyOn(plotloomApi, "patchProject"), importAsset = vi.spyOn(plotloomApi, "importManagedAsset");
  const state = await harness();
  try {
    await state.render("current"); expect(state.reader.state?.status).toBe("failed");
    expect(state.host.textContent).not.toContain("未声明局限");
    await act(async () => state.reader.retry());
    expect(state.reader.state?.status).toBe("ready"); expect(state.host.textContent).toContain("补充参考");
    expect(write).not.toHaveBeenCalled(); expect(importAsset).not.toHaveBeenCalled(); expect(assets).toHaveBeenCalledTimes(2);
  } finally { await state.unmount(); }
});

it("changing the exact bundle withdraws old ready evidence before the replacement resolves", async () => {
  const assets = mockReads(), state = await harness();
  let release!: (value: EvidenceReads) => void;
  try {
    await state.render("current", "first");
    assets.mockImplementationOnce(() => new Promise(done => { release = done; }));
    await state.render("current", "second"); expect(state.host.textContent).toBe("unknown");
    await act(async () => release(evidenceReadsFixture("current")));
    expect(state.reader.state?.status).toBe("ready");
  } finally { await state.unmount(); }
});
