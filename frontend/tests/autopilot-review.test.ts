import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AutopilotWorkspace, AutopilotLaunch, useAdoptionLabel } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { authoredSource } from "../src/features/autopilot/sourceAuthorship";
import { fixtureRun } from "./autopilot-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root; let host: HTMLDivElement;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
function Label() { const label = useAdoptionLabel(); return createElement("div", null, label("characters", 1, "cast-hash"), " / ", label("characters", 2, "manual-hash")); }
async function render(id = "disposable") { await act(async () => { root.render(createElement(AutopilotWorkspace, { projectId: id, revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
  children: createElement(Label) })); }); }
it("shows machine adoption only for the exact adopted owner revision/hash", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(fixtureRun);
  await render(); expect(host.textContent).toContain("AI 已采用 / 已确认"); expect(host.textContent).toContain("尚未获得完整人工审阅");
});
it("does not display an old project's late read after project switch", async () => {
  let release!: (value: typeof fixtureRun) => void;
  vi.spyOn(autopilotApi, "current").mockImplementation(id => id === "disposable" ? new Promise(done => { release = done; }) : Promise.resolve(null));
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: false, briefRevision: 1 });
  await render(); await render("different-project"); await act(async () => release(fixtureRun));
  expect(host.textContent).not.toContain("等待你审阅"); expect(host.textContent).toContain("已确认 / 已确认");
});
it("never offers Start for an existing manual project or unsaved Brief", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null); vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: false, briefRevision: 1 });
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "manual", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }) })));
  expect(host.textContent).not.toContain("一键准备视频素材");
});
it("author editing drops trusted Brief-origin authority without changing retained bytes", () => {
  const original = { kind: "synopsis" as const, title: "Saved title", text: "Saved synopsis", attribution: null, rightsDeclaration: null, adaptationIntent: "", inventedAdditions: null,
    briefOrigin: { kind: "saved_brief" as const, revision: 1, contentHash: "frozen" } };
  const edit = authoredSource({ ...original, text: "Human revision" });
  expect(edit).not.toHaveProperty("briefOrigin"); expect(edit.text).toBe("Human revision"); expect(original.text).toBe("Saved synopsis"); expect(original.briefOrigin.revision).toBe(1);
});
