import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { fallbackProfiles } from "../src/app/workspace/useTextProviderProfiles";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import type { ProjectResource } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
const authority = (patch = {}): ProjectResource => ({ id: "retained", revision: 4, brief: { ...demoProject.brief, title: "Server title" }, lifecycleRevision: 1, lifecycleStatus: "active", archivedAt: null, createdAt: "2026-10-04", updatedAt: "2026-10-04", ...patch });
const button = (label: string) => [...document.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === label)!;
const flush = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
const retained = () => JSON.parse(sessionStorage.getItem("plotloom:workbench-drafts:v1")!);

beforeEach(() => {
  sessionStorage.clear(); window.history.replaceState(null, "", "/?project=retained&stage=brief");
  sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ "retained:brief:4": { key: "retained:brief:4", projectId: "retained", scope: "brief", baseRevision: 4, localRevision: 1, serverDraftRevision: 0, payload: { ...demoProject.brief, title: "Retained author title" }, updatedAt: "2026-10-04" } }));
  document.body.innerHTML = '<div id="root"></div>'; root = createRoot(document.getElementById("root")!);
  vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [] });
  vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [] });
  vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue(fallbackProfiles());
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
});
afterEach(async () => { await act(async () => root.unmount()); vi.restoreAllMocks(); });

it("retains authored content through temporary failure and explicitly retries and revalidates before restoring", async () => {
  const read = vi.spyOn(plotloomApi, "getProject").mockRejectedValueOnce(new TypeError("temporary network failure")).mockResolvedValue(authority());
  const write = vi.spyOn(plotloomApi, "patchProject");
  await act(async () => root.render(createElement(App))); await flush();
  expect(document.body.textContent).toContain("暂时无法核实项目，草稿已保留");
  const inspection = document.querySelector<HTMLTextAreaElement>('[aria-label="保留的草稿"]')!;
  expect(inspection.readOnly).toBe(true); expect(inspection.value).toContain("Retained author title");
  await act(async () => button("重试核实项目").click()); await flush();
  expect(button("恢复草稿")).toBeDefined();
  expect(retained()["retained:brief:4"]).toBeDefined(); expect(write).not.toHaveBeenCalled();
  await act(async () => button("恢复草稿").click()); await flush();
  expect(read).toHaveBeenCalledTimes(3); // Aggregate failure, retry, exact restore revalidation.
  expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("Retained author title");
  expect(write).not.toHaveBeenCalled();
});

it("keeps retained drafts while allowing Home navigation after explicit keep", async () => {
  vi.spyOn(plotloomApi, "getProject").mockRejectedValue(new TypeError("offline"));
  const write = vi.spyOn(plotloomApi, "patchProject");
  await act(async () => root.render(createElement(App))); await flush();
  await act(async () => (document.querySelector('.brand-home') as HTMLButtonElement).click());
  await act(async () => button("保留草稿，稍后重试").click()); await flush();
  expect(document.body.textContent).toContain("从一个项目开始");
  expect(retained()["retained:brief:4"]).toBeDefined(); expect(write).not.toHaveBeenCalled();
});

it.each(["revision", "foreign", "archived", "deleted", "temporary"])("refuses restoration and exposes usable recovery if exact authority changes to %s", async defect => {
  const next = defect === "revision" ? authority({ revision: 5 }) : defect === "foreign" ? authority({ id: "foreign" }) : authority({ lifecycleStatus: "archived", archivedAt: "2026-10-04" });
  const read = vi.spyOn(plotloomApi, "getProject").mockResolvedValueOnce(authority());
  if (defect === "deleted") read.mockRejectedValue(new ApiError("missing", 404));
  else if (defect === "temporary") read.mockRejectedValue(new TypeError("offline"));
  else read.mockResolvedValue(next);
  const write = vi.spyOn(plotloomApi, "patchProject");
  await act(async () => root.render(createElement(App))); await flush();
  await act(async () => button("恢复草稿").click()); await flush();
  expect(document.body.textContent).toContain("草稿未恢复");
  expect(button("恢复草稿")).toBeUndefined();
  expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("Server title");
  expect(retained()["retained:brief:4"]).toBeDefined(); expect(write).not.toHaveBeenCalled();
  if (defect === "revision") {
    expect(button("复制草稿为新项目")).toBeDefined();
    await act(async () => button("重新加载服务器版本").click()); await flush();
    expect(button("已加载服务器版本")).toBeDefined();
    expect(retained()["retained:brief:4"].baseRevision).toBe(4);
  } else {
    const inspection = document.querySelector<HTMLTextAreaElement>('[aria-label="保留的草稿"]')!;
    expect(inspection.readOnly).toBe(true); expect(inspection.value).toContain("Retained author title");
    expect(document.body.textContent).toContain(defect === "archived" ? "归档项目草稿不可恢复" : defect === "deleted" ? "原项目不存在，草稿已保留" : "暂时无法核实项目，草稿已保留");
    expect(button("复制保留内容")).toBeDefined(); expect(button("导出保留内容")).toBeDefined();
    await act(async () => button("保留草稿，稍后重试").click()); await flush();
    expect(document.querySelector('[aria-label="保留的草稿"]')).toBeNull();
    expect(retained()["retained:brief:4"].baseRevision).toBe(4);
  }
  expect(write).not.toHaveBeenCalled();
});

it.each(["project", "auxiliary"])("distinguishes %s 404 without erasing retained input", async target => {
  const error = new ApiError("missing", 404);
  const read = vi.spyOn(plotloomApi, "getProject");
  if (target === "project") read.mockRejectedValue(error); else read.mockResolvedValue(authority());
  if (target === "auxiliary") vi.mocked(plotloomApi.getStages).mockRejectedValue(error);
  await act(async () => root.render(createElement(App))); await flush();
  expect(document.body.textContent).toContain(target === "project" ? "原项目不存在，草稿已保留" : "暂时无法核实项目，草稿已保留");
  expect(button("恢复草稿")).toBeUndefined(); expect(retained()["retained:brief:4"]).toBeDefined();
});

it.each([false, true])("explicit unsafe discard cannot resurrect its conflict lineage or erase an unrelated record (newer typing: %s)", async newerTyping => {
  const unrelated = { ...retained()["retained:brief:4"], key: "other:brief:4", projectId: "other", payload: { title: "Other project input" } };
  sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ ...retained(), [unrelated.key]: unrelated }));
  const read = vi.spyOn(plotloomApi, "getProject").mockResolvedValue(authority({ revision: 5 }));
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft"), copy = vi.spyOn(plotloomApi, "createProject"), discard = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  await act(async () => root.render(createElement(App))); await flush();
  expect(button("复制草稿为新项目")).toBeDefined();
  if (newerTyping) {
    const all = retained(), selected = all["retained:brief:4"];
    sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ ...all, [selected.key]: {
      ...selected, localRevision: 2, payload: { ...selected.payload, title: "Latest retained typing" },
    } }));
  }
  read.mockRejectedValueOnce(new TypeError("offline during conflict reload"));
  await act(async () => button("重新加载服务器版本").click()); await flush();
  expect(button("丢弃不可用草稿")).toBeDefined();
  await act(async () => button("丢弃不可用草稿").click()); await flush();
  expect(document.body.textContent).not.toContain("草稿版本已过期");
  expect(button("复制草稿为新项目")).toBeUndefined(); expect(button("恢复草稿")).toBeUndefined();
  expect(retained()["retained:brief:4"]).toBeUndefined(); expect(retained()[unrelated.key]).toEqual(unrelated);
  expect(document.querySelector(".workspace-copy-notice[role=status]")?.textContent).toContain("已丢弃本标签页选中的保留草稿。项目中已保存的草稿和已确认内容未删除。");
  expect(document.body.textContent).toContain("offline during conflict reload");
  expect(Element.prototype.scrollIntoView).toHaveBeenCalledExactlyOnceWith({ block: "center", inline: "nearest" });
  expect(write).not.toHaveBeenCalled(); expect(copy).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled();
  if (newerTyping) {
    await act(async () => (document.querySelector('.brand-home') as HTMLButtonElement).click()); await flush();
  } else {
    await act(async () => button("知道了").click()); await flush();
  }
  expect(document.querySelector(".workspace-copy-notice[role=status]")).toBeNull();
});

it("requires a fresh discard decision if the selected retained revision changes", async () => {
  vi.spyOn(plotloomApi, "getProject").mockRejectedValue(new TypeError("offline"));
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft"), discard = vi.spyOn(plotloomApi, "discardAuthoringDraft");
  await act(async () => root.render(createElement(App))); await flush();
  const newer = { ...retained()["retained:brief:4"], localRevision: 2, payload: { ...demoProject.brief, title: "Newer retained input" } };
  sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ [newer.key]: newer }));
  await act(async () => button("丢弃不可用草稿").click()); await flush();
  expect(retained()[newer.key]).toEqual(newer);
  expect(document.body.textContent).toContain("保留草稿已变化，请查看最新内容后再丢弃");
  expect(document.body.textContent).not.toContain("已丢弃本标签页选中的保留草稿");
  expect((document.querySelector('[aria-label="保留的草稿"]') as HTMLTextAreaElement).value).toContain("Newer retained input");
  expect(write).not.toHaveBeenCalled(); expect(discard).not.toHaveBeenCalled();
});
