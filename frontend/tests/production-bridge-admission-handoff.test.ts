import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ProductionBridgePanel } from "../src/pages/ProductionBridgePanel";
import type { ProductionBridgeState } from "../src/types";
import { bridgeState, installedProduction } from "./production-bridge-fixture";

let handoff: ((id: string) => void) | undefined;
vi.mock("../src/pages/InstalledProductionSummary", () => ({
  InstalledProductionSummary: ({ onOpenShot }: { onOpenShot?: (id: string) => void }) => { handoff = onOpenShot; return null; },
}));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
const installed = () => bridgeState({ status: "accepted", installation: installedProduction() });
const open = vi.fn();
const render = async (revision = 1, projectId = "project") => { await act(async () => root.render(createElement(ProductionBridgePanel, {
  projectId, reviewBasis: { revision, contentHash: String(revision).repeat(64), status: "current" },
  readOnly: false, onOpenShot: open, onInstalled: async () => undefined,
}))); };
beforeEach(() => { root = createRoot(document.createElement("div")); handoff = undefined; open.mockClear(); });
afterEach(async () => { await act(async () => root.unmount()); vi.restoreAllMocks(); });

it.each(["same-basis refresh", "changed basis", "changed project"])("rejects an installed-shot callback retained before %s", async change => {
  let resolve!: (value: ProductionBridgeState) => void;
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValueOnce(installed()).mockReturnValue(new Promise(done => { resolve = done; }));
  await render(); const retained = handoff!;
  retained("first"); expect(open).toHaveBeenCalledExactlyOnceWith("first"); open.mockClear();
  if (change === "same-basis refresh") await act(async () => window.dispatchEvent(new Event("plotloom-specialists-changed")));
  else await render(change === "changed basis" ? 2 : 1, change === "changed project" ? "other" : "project");
  retained("obsolete"); expect(open).not.toHaveBeenCalled();
  await act(async () => resolve(installed()));
  retained("still-obsolete"); expect(open).not.toHaveBeenCalled();
  handoff!("current"); expect(open).toHaveBeenCalledExactlyOnceWith("current");
});
