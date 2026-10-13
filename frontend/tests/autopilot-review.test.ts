import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AutopilotWorkspace, AutopilotLaunch, useAdoptionLabel, useAutopilot } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { authoredSource } from "../src/features/autopilot/sourceAuthorship";
import { fixtureRun, fixtureMaterial } from "./autopilot-fixture";
import { MaterialReview } from "../src/features/autopilot/MaterialReview";
import { StoryboardReviewPanel } from "../src/pages/StoryboardReviewPanel";
import { plotloomApi } from "../src/api";
import { specialistsApi } from "../src/features/specialists/api";
import { projectAutopilotProgress } from "../src/features/autopilot/progress";
import type { AcceptedStoryboardReviewRevision } from "../src/types";

vi.mock("../src/pages/ProductionBridgePanel", () => ({ ProductionBridgePanel: () => null }));

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root; let host: HTMLDivElement;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });
function Label() { const label = useAdoptionLabel(); return createElement("div", null, label("characters", 1, "cast-hash"), " / ", label("characters", 2, "manual-hash")); }
async function render(id = "disposable") { await act(async () => { root.render(createElement(AutopilotWorkspace, { projectId: id, revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
  children: createElement(Label) })); }); }
it("projects inventory-bound reference and provisional-frame progress once", () => {
  const run = { ...fixtureRun, state: "running" as const,
    bundle: { inventory: { subjects: [
      { owner: "character-reference", id: "hero" }, { owner: "art-reference", subjectType: "scene" as const, id: "harbor" },
      { owner: "image", id: "shot-1" }, { owner: "image", id: "shot-2" },
    ] }, frames: [], references: [] },
    checkpoints: [
      { operationKey: "character-reference:hero", state: "adopted", evidence: { owner: "character-reference", result: {} } },
      { operationKey: "art-reference:scene:harbor", state: "adopted", evidence: { owner: "art-reference", result: {} } },
    ],
    frames: [{ shotId: "shot-1" }, { shotId: "shot-1" }, { shotId: "orphan-shot" }],
  };
  expect(projectAutopilotProgress(run)).toMatchObject({ imagesSelected: 3, imagesRequired: 4 });
});
it("projects complete image progress from the frozen inventory and hides stale evidence", () => {
  const complete = { ...fixtureRun, state: "awaiting_review" as const,
    bundle: { inventory: { subjects: [{ owner: "image", id: "shot-1" }] }, frames: [], references: [] },
    frames: [{ shotId: "shot-1" }] };
  expect(projectAutopilotProgress(complete).imagesSelected).toBe(1);
  expect(projectAutopilotProgress({ ...complete, state: "stale" }).imagesSelected).toBe(0);
  for (const state of ["cancelled", "taken_over"] as const) {
    expect(projectAutopilotProgress({ ...complete, state, blocker: { code: "material_changed", message: "source changed" } }).imagesSelected).toBe(0);
  }
});
it("shows machine adoption only for the exact adopted owner revision/hash", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(fixtureRun);
  await render(); expect(host.textContent).toContain("AI 已采用 / 已采用 · 来源待核实"); expect(host.textContent).toContain("尚未获得完整人工审阅");
});
it("keeps labels neutral until provenance is successfully read", async () => {
  let release!: (value: typeof fixtureRun) => void;
  vi.spyOn(autopilotApi, "current").mockImplementation(() => new Promise(done => { release = done; }));
  await render(); expect(host.textContent).toContain("已采用 · 来源待核实 / 已采用 · 来源待核实");
  expect(host.textContent).not.toContain("已确认");
  await act(async () => release(fixtureRun)); expect(host.textContent).toContain("AI 已采用 / 已采用 · 来源待核实");
});
it("read failure never turns unknown AI provenance into human confirmation", async () => {
  vi.spyOn(autopilotApi, "current").mockRejectedValue(new Error("fixture unavailable"));
  await render(); expect(host.textContent).toContain("来源待核实"); expect(host.textContent).not.toContain("已确认");
  expect(host.textContent).toContain("fixture unavailable");
});
it("fresh no-run Start begins polling through server progress to review without navigation or revision change", async () => {
  vi.useFakeTimers();
  const running = { ...fixtureRun, state: "running" as const, phase: "references", revision: 13 };
  const read = vi.spyOn(autopilotApi, "current").mockResolvedValueOnce(null).mockResolvedValueOnce(running).mockResolvedValue({ ...fixtureRun, revision: 14 });
  vi.spyOn(autopilotApi, "start").mockResolvedValue({ ...running, revision: 12 });
  function Start() { const owner = useAutopilot()!; return createElement("button", { onClick: () => void owner.start({ styleAuthority: "preset", renderStyle: "live-action", artRenderStyle: "live-action", maxImages: 80, maxJobs: 96 }) }, "start fixture"); }
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined, children: createElement(Start) })));
  expect(read).toHaveBeenCalledTimes(1);
  await act(async () => host.querySelector<HTMLButtonElement>("button")!.click());
  expect(read).toHaveBeenCalledTimes(2); expect(host.textContent).toContain("参考图片");
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(read).toHaveBeenCalledTimes(3); expect(host.textContent).toContain("等待你审阅");
});
it("retries transient progress read errors and restores exact provenance without replay", async () => {
  vi.useFakeTimers();
  const read = vi.spyOn(autopilotApi, "current").mockResolvedValueOnce({ ...fixtureRun, state: "running" }).mockRejectedValueOnce(new Error("temporary fixture error")).mockResolvedValue(fixtureRun);
  const send = vi.spyOn(autopilotApi, "start");
  await render(); await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(host.textContent).toContain("temporary fixture error"); expect(host.textContent).toContain("来源待核实"); expect(host.textContent).not.toContain("已确认");
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(read).toHaveBeenCalledTimes(3); expect(send).not.toHaveBeenCalled(); expect(host.textContent).toContain("AI 已采用"); expect(host.textContent).toContain("等待你审阅");
});
it("reads an admitted run after an uncertain Start response and retains the command error without replay", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValueOnce(null).mockResolvedValue(fixtureRun);
  const start = vi.spyOn(autopilotApi, "start").mockRejectedValue(new Error("Start acknowledgment lost"));
  function Start() { const owner = useAutopilot()!; return createElement("button", { onClick: () => void owner.start({ styleAuthority: "preset", renderStyle: "live-action", artRenderStyle: "live-action", maxImages: 80, maxJobs: 96 }) }, "start fixture"); }
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined, children: createElement(Start) })));
  await act(async () => host.querySelector<HTMLButtonElement>("button")!.click());
  expect(start).toHaveBeenCalledOnce(); expect(host.textContent).toContain("等待你审阅"); expect(host.textContent).toContain("Start acknowledgment lost");
});
it.each(["reference", "frame"])("observes handoff withdrawal after a %s edit without changing Brief", async edit => {
  vi.useFakeTimers();
  const reviewed = { ...fixtureRun, state: "handed_off" as const, handoff: { receiptId: "previous-human" } };
  const read = vi.spyOn(autopilotApi, "current").mockResolvedValueOnce(reviewed).mockResolvedValue({ ...reviewed, state: "taken_over", revision: 13, blocker: { code: "material_changed", message: `${edit} changed` } });
  const video = vi.fn();
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: video, children: createElement(Label) })));
  expect(host.textContent).toContain("已记录完整人工审阅"); expect(host.textContent).toContain("进入手动视频制作");
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(read).toHaveBeenCalledTimes(2); expect(host.textContent).toContain(`${edit} changed`);
  expect(host.textContent).toContain("尚未获得完整人工审阅"); expect(host.textContent).not.toContain("进入手动视频制作"); expect(video).not.toHaveBeenCalled();
});
it("unreadable handoff currentness hides manual video entrance until a successful read", async () => {
  vi.useFakeTimers();
  const reviewed = { ...fixtureRun, state: "handed_off" as const, handoff: { receiptId: "previous-human" } };
  vi.spyOn(autopilotApi, "current").mockResolvedValueOnce(reviewed).mockRejectedValueOnce(new Error("currentness unavailable")).mockResolvedValue(reviewed);
  await render(); await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(host.textContent).toContain("人工审阅状态待核实"); expect(host.textContent).not.toContain("已记录完整人工审阅"); expect(host.textContent).not.toContain("进入手动视频制作");
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(host.textContent).toContain("进入手动视频制作");
});
it("does not display an old project's late read after project switch", async () => {
  let release!: (value: typeof fixtureRun) => void;
  vi.spyOn(autopilotApi, "current").mockImplementation(id => id === "disposable" ? new Promise(done => { release = done; }) : Promise.resolve(null));
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: false, briefRevision: 1 });
  await render(); await render("different-project"); await act(async () => release(fixtureRun));
  expect(host.textContent).not.toContain("等待你审阅"); expect(host.textContent).toContain("已确认 / 已确认");
});
it("keeps automatic Start disabled for an existing manual project", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null); vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: false, briefRevision: 1 });
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "manual", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }) })));
  expect(host.textContent).toContain("自动准备素材");
  expect(host.querySelector<HTMLButtonElement>('button')!.disabled).toBe(true);
});
it("retries launch-context observation without replaying a command", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  const read = vi.spyOn(autopilotApi, "launchContext").mockRejectedValueOnce(new Error("launch read failed"))
    .mockResolvedValue({ eligible: true, briefRevision: 1 });
  const start = vi.spyOn(autopilotApi, "start");
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "retry-project", revision: 1,
    readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }) })));
  const launch = () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!;
  expect(launch().disabled).toBe(true);
  expect(host.textContent).toContain("重试核对");
  await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "重试核对")!.click());
  expect(read).toHaveBeenCalledTimes(2);
  expect(launch().disabled).toBe(false);
  expect(start).not.toHaveBeenCalled();
});
it("a late eligible launch-context read from the previous project cannot enable the new project", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  const start = vi.spyOn(autopilotApi, "start");
  let release!: (value: { eligible: boolean; briefRevision: number }) => void;
  const read = vi.spyOn(autopilotApi, "launchContext").mockImplementationOnce(() => new Promise(done => { release = done; }))
    .mockResolvedValue({ eligible: false, briefRevision: 1 });
  const draw = async (projectId: string) => act(async () => root.render(createElement(AutopilotWorkspace, {
    projectId, revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }),
  })));
  await draw("previous-project"); const previousSignal = read.mock.calls[0][1]!;
  await draw("current-project"); expect(previousSignal.aborted).toBe(true);
  await act(async () => release({ eligible: true, briefRevision: 1 }));
  const launch = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!;
  expect(launch.disabled).toBe(true);
  expect(start).not.toHaveBeenCalled();
});
it("refreshes admission after exact draft cleanup without changing Brief or replaying Start", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  const read = vi.spyOn(autopilotApi, "launchContext").mockResolvedValueOnce({ eligible: false, briefRevision: 1 }).mockResolvedValue({ eligible: true, briefRevision: 1 });
  const start = vi.spyOn(autopilotApi, "start");
  const draw = async (admissionVersion: number) => act(async () => root.render(createElement(AutopilotWorkspace, {
    projectId: "disposable", revision: 1, admissionVersion, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }),
  })));
  await draw(0); expect(host.textContent).toContain("自动准备素材");
  let launch = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!;
  expect(launch.disabled).toBe(true);
  await draw(1); expect(host.textContent).toContain("自动准备素材");
  launch = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!;
  expect(launch.disabled).toBe(false);
  expect(read).toHaveBeenCalledTimes(2); expect(start).not.toHaveBeenCalled();
});
it("aborts superseded admission reads and retains server refusal for manual material", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  const start = vi.spyOn(autopilotApi, "start");
  let release!: (value: { eligible: boolean; briefRevision: number }) => void;
  const read = vi.spyOn(autopilotApi, "launchContext").mockImplementationOnce(() => new Promise(done => { release = done; }))
    .mockResolvedValue({ eligible: false, briefRevision: 1 });
  const draw = async (id: string, admissionVersion: number) => act(async () => root.render(createElement(AutopilotWorkspace, {
    projectId: id, revision: 1, admissionVersion, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }),
  })));
  await draw("previous", 0); const signal = read.mock.calls[0][1]!;
  await draw("manual", 1); expect(signal.aborted).toBe(true);
  await act(async () => release({ eligible: true, briefRevision: 1 }));
  expect(host.textContent).toContain("自动准备素材"); expect(read).toHaveBeenCalledTimes(2);
  expect([...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!.disabled).toBe(true);
  expect(start).not.toHaveBeenCalled();
});
it("withdraws a previously eligible launch while a newer mutation observation is pending", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  const start = vi.spyOn(autopilotApi, "start");
  let release!: (value: { eligible: boolean; briefRevision: number }) => void;
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValueOnce({ eligible: true, briefRevision: 1 })
    .mockImplementationOnce(() => new Promise(done => { release = done; }));
  const draw = async (admissionVersion: number) => act(async () => root.render(createElement(AutopilotWorkspace, {
    projectId: "disposable", revision: 1, admissionVersion, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }),
  })));
  await draw(0); expect(host.textContent).toContain("自动准备素材");
  const launch = () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "自动准备素材")!;
  expect(launch().disabled).toBe(false);
  await draw(1); expect(host.textContent).toContain("自动准备素材");
  expect(launch().disabled).toBe(true);
  await act(async () => release({ eligible: false, briefRevision: 1 }));
  expect(launch().disabled).toBe(true);
  expect([...host.querySelectorAll<HTMLButtonElement>("button")].some(item => item.textContent === "开始准备已保存简报的素材")).toBe(false);
  expect(start).not.toHaveBeenCalled();
});
it("submits explicit Brief authority by default and blocks a duplicate slow Start", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: true, briefRevision: 1 });
  vi.spyOn(specialistsApi, "settings").mockResolvedValue({
    text: { name: "文字助手", taskId: "text-task" }, image: { name: "图像助手", taskId: "image-task" }, busy: false,
  });
  let release!: (value: typeof fixtureRun) => void;
  const start = vi.spyOn(autopilotApi, "start").mockImplementation(() => new Promise(resolve => { release = resolve; }));
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1,
    readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false,
      visualDirection: "2D 动画；水彩；低饱和；保留细节" }) })));
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  await act(async () => host.querySelector<HTMLButtonElement>('button')!.click());
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(host.textContent).toContain("2D 动画；水彩；低饱和；保留细节");
  const submit = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "开始准备已保存简报的素材")!;
  await act(async () => submit.click());
  const pending = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "正在开始自动准备…")!;
  expect(pending.disabled).toBe(true);
  expect(pending.getAttribute("aria-busy")).toBe("true");
  expect(pending.querySelector(".autopilot-activity-indicator")).not.toBeNull();
  expect(start).toHaveBeenCalledOnce();
  expect(start.mock.calls[0][1]).toMatchObject({ styleAuthority: "brief", maxImages: 80, maxJobs: 96 });
  await act(async () => release(fixtureRun));
});
it("does not offer another Start while a rejected or unknown Start is being reconciled", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValueOnce(null).mockRejectedValueOnce(new Error("run receipt unavailable"));
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: true, briefRevision: 1 });
  vi.spyOn(specialistsApi, "settings").mockResolvedValue({
    text: { name: "文字助手", taskId: "text-task" }, image: { name: "图像助手", taskId: "image-task" }, busy: false,
  });
  const start = vi.spyOn(autopilotApi, "start").mockRejectedValue(new Error("response unknown"));
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1,
    readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }) })));
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  await act(async () => host.querySelector<HTMLButtonElement>('button')!.click());
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  const submit = [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === "开始准备已保存简报的素材")!;
  await act(async () => submit.click());
  await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
  expect(start).toHaveBeenCalledOnce();
  expect(host.textContent).toContain("核对完成前不会重复启动");
  expect(host.textContent).not.toContain("开始准备已保存简报的素材");
});
it("author editing drops trusted Brief-origin authority without changing retained bytes", () => {
  const original = { kind: "synopsis" as const, title: "Saved title", text: "Saved synopsis", attribution: null, rightsDeclaration: null, adaptationIntent: "", inventedAdditions: null,
    briefOrigin: { kind: "saved_brief" as const, revision: 1, contentHash: "frozen" } };
  const edit = authoredSource({ ...original, text: "Human revision" });
  expect(edit).not.toHaveProperty("briefOrigin"); expect(edit.text).toBe("Human revision"); expect(original.text).toBe("Saved synopsis"); expect(original.briefOrigin.revision).toBe(1);
});
it("a review already open becomes read-only with its workspace and keeps close available", async () => {
  vi.spyOn(autopilotApi, "review").mockResolvedValue(fixtureMaterial);
  const submit = vi.spyOn(autopilotApi, "handoff");
  const props = { projectId: "disposable", onClose: () => undefined, onAccepted: async () => undefined, onUncertain: () => undefined };
  await act(async () => root.render(createElement(MaterialReview, props)));
  expect(host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.disabled).toBe(false);
  await act(async () => root.render(createElement(MaterialReview, { ...props, readOnly: true })));
  expect([...host.querySelectorAll("input, textarea, select")].every(element => element.matches(":disabled"))).toBe(true);
  expect(host.querySelector<HTMLButtonElement>("button")!.disabled).toBe(false);
  expect(submit).not.toHaveBeenCalled();
});
it.each(["ai", "manual", "failed"])("storyboard header, guide and reader carry %s provenance consistently", async kind => {
  const accepted: AcceptedStoryboardReviewRevision = { revision: 1, candidateJobId: "fixture-board", contentHash: "board-hash",
    binding: { scriptRevision: 1 } as AcceptedStoryboardReviewRevision["binding"], storyboard: { episodes: [] }, acceptedAt: "2026-10-12T00:00:00Z" };
  vi.spyOn(plotloomApi, "getStoryboardSourceReview").mockResolvedValue({ candidate: null, acceptedReview: accepted, status: "accepted", staleReasons: [],
    acceptedReviewState: { status: "current", staleReasons: [] } });
  const read = vi.spyOn(autopilotApi, "current");
  if (kind === "ai") read.mockResolvedValue({ ...fixtureRun, checkpoints: [{ operationKey: "storyboard", state: "adopted", evidence: { owner: "storyboard", result: { revision: 1, contentHash: "board-hash" } } }] });
  else if (kind === "manual") read.mockResolvedValue(null);
  else read.mockRejectedValue(new Error("unavailable provenance"));
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(StoryboardReviewPanel, { projectId: "disposable", readOnly: true, onInstalled: async () => undefined }) })));
  const panel = host.querySelector('[data-testid="storyboard-review"]')!;
  const label = kind === "ai" ? "AI 已采用" : kind === "manual" ? "已确认" : "来源待核实";
  expect(panel.querySelector("header strong")!.textContent).toContain(label);
  expect(panel.textContent).toContain(kind === "ai" ? "AI 已采用分镜评审" : kind === "manual" ? "分镜评审已确认" : "采用来源尚待核实");
  const disclosure = [...panel.querySelectorAll("summary")].find(node => node.textContent?.startsWith("查看当前"));
  expect(disclosure?.textContent).toContain(label);
  if (kind !== "manual") expect(panel.querySelector("header strong")!.textContent).not.toContain("已确认");
});
