import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { fallbackProfiles } from "../src/app/workspace/useTextProviderProfiles";

// Inspect the navigation owner's contract, independently of review read fixtures.
vi.mock("../src/pages/SourceOutlinePage", () => ({
  SourceOutlinePage: ({ navigationTarget }: { navigationTarget: string }) =>
    createElement("div", { "data-testid": "refresh-source-route", "data-target": navigationTarget }),
}));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
beforeEach(() => {
  document.body.innerHTML = '<div id="test-root"></div>'; sessionStorage.clear();
  root = createRoot(document.getElementById("test-root")!);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ id: "project", revision: 1, brief: demoProject.brief,
    lifecycleRevision: 1, lifecycleStatus: "active", archivedAt: null, createdAt: "now", updatedAt: "now" });
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [] });
  vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [] });
  vi.spyOn(plotloomApi, "getRuntimeCapabilities").mockResolvedValue({ durableProjectDrafts: false, explicitProjectClose: true,
    portableSnapshots: true, durableMediaDrafts: false, apiTextPipeline: true });
  vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue(fallbackProfiles());
  vi.spyOn(plotloomApi, "listProjects").mockResolvedValue({ projects: [], nextCursor: null });
});
afterEach(async () => { await act(async () => root.unmount()); vi.restoreAllMocks(); });
const flush = async () => { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); };

it.each(["source", "art", "script", "storyboard-review"])("toolbar refresh preserves the mounted %s route and URL", async target => {
  const url = `/?project=project&stage=source#${target}`;
  history.replaceState(null, "", url);
  await act(async () => root.render(createElement(App))); await flush();
  const panel = document.querySelector('[data-testid="refresh-source-route"]')!;
  expect(panel.getAttribute("data-target")).toBe(target);
  const refresh = [...document.querySelectorAll("button")].find(button => button.textContent === "刷新服务器版本")!;
  await act(async () => refresh.click()); await flush();
  expect(plotloomApi.getProject).toHaveBeenCalledTimes(2);
  expect(document.querySelector('[data-testid="refresh-source-route"]')).toBe(panel);
  expect(panel.getAttribute("data-target")).toBe(target);
  expect(location.search + location.hash).toBe(url.slice(1));
});
