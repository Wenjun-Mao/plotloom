import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Button, Field } from "../src/components";
import { CastPanel } from "../src/pages/CastPanel";
import { BriefPage } from "../src/pages/BriefPage";
import { QuarantinePage } from "../src/pages/QuarantinePage";
import { demoProject, demoRun } from "../src/demo";
import { specialistsApi } from "../src/features/specialists/api";
import { plotloomApi } from "../src/api";
import { TracePage } from "../src/pages/TracePage";
import type { CastReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "prepared", configured: false });
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

const accepted: NonNullable<CastReviewState["acceptedCast"]> = {
  revision: 1, candidateJobId: "old-job", contentHash: "a".repeat(64), acceptedAt: "2026-10-04T00:00:00Z",
  cast: { characters: [{ id: "lin", name: "林遥", persona: { personality: ["克制"], appearance: "深色外套" } }] },
  consumerMappings: [], reportAvailable: false, differsFromDelivery: null,
  binding: { sourceRevision: 1, sourceContentHash: "b", outlineRevision: 1, outlineContentHash: "c", sectionMapRevision: 1, sectionMapContentHash: "d", graphRevision: 1, graphContentHash: "e", sectionIds: ["opening"] },
};
const props = { projectId: "project", readOnly: false, loadError: "", onState: vi.fn(), onRefresh: vi.fn(async () => true), onInvalidate: vi.fn(), onTransitionComplete: vi.fn() };
async function renderCast(state?: CastReviewState, loadError = "") {
  await act(async () => root.render(createElement(CastPanel, { ...props, state, loadError })));
}

it("marks required labels inline without giving optional inputs a native validation constraint", async () => {
  await act(async () => root.render(createElement(Field, { label: "故事内容", required: true, children: createElement("textarea", { "aria-required": true }) })));
  expect(host.querySelector(".field > label")?.textContent).toBe("故事内容 *");
  expect(host.querySelector(".required-mark")?.getAttribute("aria-hidden")).toBe("true");
  expect(host.querySelector("textarea")?.hasAttribute("required")).toBe(false);
  expect(host.querySelector("textarea")?.getAttribute("aria-required")).toBe("true");
});

it.each(["input", "select", "textarea"])("keeps %s field names separate from help text and retains existing descriptions", async (control) => {
  await act(async () => root.render(createElement(Field, {
    label: "一句话概述", hint: "详细背景写在故事前提中。",
    children: createElement(control, { "aria-describedby": "existing-help" }),
  })));
  const input = host.querySelector(control)!;
  const label = host.querySelector("label")!;
  const descriptionIds = input.getAttribute("aria-describedby")!.split(" ");
  expect(label.textContent).toBe("一句话概述");
  expect(label.htmlFor).toBe(input.id);
  expect(descriptionIds[0]).toBe("existing-help");
  expect(document.getElementById(descriptionIds[1])?.textContent).toBe("详细背景写在故事前提中。");
  expect(label.contains(document.getElementById(descriptionIds[1]))).toBe(false);
});

it("preserves explicit control names and custom field children", async () => {
  await act(async () => root.render(createElement(Field, {
    label: "通用字段", hint: "说明", children: [
      createElement("input", { key: "named", "aria-label": "专用字段" }),
      createElement("textarea", { key: "referenced", "aria-labelledby": "external-label" }),
      createElement("div", { key: "custom", "data-testid": "custom" }, "自定义控件"),
    ],
  })));
  expect(host.querySelector("input")?.getAttribute("aria-label")).toBe("专用字段");
  expect(host.querySelector("input")?.hasAttribute("aria-labelledby")).toBe(false);
  expect(host.querySelector("textarea")?.getAttribute("aria-labelledby")).toBe("external-label");
  expect(host.querySelector('[data-testid="custom"]')?.textContent).toBe("自定义控件");
  expect(host.querySelector(".field")?.getAttribute("role")).toBe("group");
});

it.each(["aria-label", "aria-labelledby"])("preserves a single control's explicit id and %s when adding help", async (nameAttribute) => {
  await act(async () => root.render(createElement(Field, {
    label: "通用字段", hint: "新说明",
    children: createElement("input", { id: "owned-control", [nameAttribute]: "explicit-name", "aria-describedby": "existing-help" }),
  })));
  const control = host.querySelector("input")!;
  expect(control.id).toBe("owned-control");
  expect(control.getAttribute(nameAttribute)).toBe("explicit-name");
  expect(host.querySelector("label")?.control).toBe(control);
  const descriptions = control.getAttribute("aria-describedby")!.split(" ");
  expect(descriptions[0]).toBe("existing-help");
  expect(document.getElementById(descriptions[1])?.textContent).toBe("新说明");
});

it("exposes busy separately from unavailable while keeping the caller's disable authority", async () => {
  await act(async () => root.render(createElement(Button, { busy: true, disabled: true }, "正在保存…")));
  expect(host.querySelector("button")?.getAttribute("aria-busy")).toBe("true");
  expect(host.querySelector("button")?.disabled).toBe(true);
  await act(async () => root.render(createElement(Button, { variant: "quiet" }, "设置")));
  expect(host.querySelector("button")?.hasAttribute("aria-busy")).toBe(false);
  expect(host.querySelector("button")?.disabled).toBe(false);
});

it("does not claim validation success from an empty quarantine projection", async () => {
  await act(async () => root.render(createElement(QuarantinePage, {
    items: [], repairing: false, onRepair: vi.fn(async () => {}), onRebuildStage: vi.fn(async () => {}),
  })));
  expect(host.textContent).toContain("当前未显示隔离结果");
  expect(host.textContent).toContain("符合修复条件时，可以只重做其中一个任务");
  expect(host.textContent).not.toContain("所有阶段输出都已通过合同验证");
});

it("explains the empty trace's actual next action without initiating a run", async () => {
  const onRun = vi.fn(async () => {});
  await act(async () => root.render(createElement(TracePage, {
    trace: [], running: false, onRun, onResume: vi.fn(async () => {}), onCancel: vi.fn(async () => {}),
  })));
  expect(host.textContent).toContain("运行事件");
  expect(host.textContent).toContain("事件详情");
  expect(host.textContent).toContain("勾选要生成的阶段，再点击“运行所选阶段”启动任务");
  expect(host.textContent).not.toContain("pipeline run");
  expect(onRun).not.toHaveBeenCalled();
});

it.each([undefined, { ...demoRun, status: "running" as const }])("waits for empty active trace events without telling the user to start again", async (run) => {
  const onRun = vi.fn(async () => {});
  await act(async () => root.render(createElement(TracePage, {
    run, trace: [], running: true, onRun, onResume: vi.fn(async () => {}), onCancel: vi.fn(async () => {}),
  })));
  expect(host.textContent).toContain("正在等待运行事件");
  expect(host.textContent).toContain("无需再次启动任务");
  expect(host.textContent).not.toContain("勾选要生成的阶段，再点击");
  expect(onRun).not.toHaveBeenCalled();
});

it("does not interpret a recorded task's empty event list as no task or success", async () => {
  await act(async () => root.render(createElement(TracePage, {
    run: demoRun, trace: [], running: false, onRun: vi.fn(async () => {}), onResume: vi.fn(async () => {}), onCancel: vi.fn(async () => {}),
  })));
  expect(host.textContent).toContain("当前任务暂无事件记录");
  expect(host.textContent).toContain("暂无事件记录不代表任务已通过");
  expect(host.textContent).not.toContain("勾选要生成的阶段，再点击");
});

it("states that Brief edits retain production and leave the separate source unchanged", async () => {
  await act(async () => root.render(createElement(BriefPage, {
    value: demoProject.brief, hasSavedProject: true, saving: false,
    onSave: vi.fn(async () => {}), onSaveAndContinue: vi.fn(async () => {}),
  })));
  expect(host.textContent).toContain("不会自动重建或替换现有制作内容");
  expect(host.textContent).toContain("故事来源正文独立保存，不会随简报梗概的修改而改变");
  expect(host.textContent).not.toContain("已安装投产");
});

it("keeps both legacy generation controls disabled when a ready Brief is read-only", async () => {
  const onGenerateProposal = vi.fn(async () => {});
  const onGenerateStoryboard = vi.fn(async () => {});
  const briefProps = { value: demoProject.brief, hasSavedProject: true, saving: false, readOnly: true,
    onSave: vi.fn(async () => {}), onSaveAndContinue: vi.fn(async () => {}),
    bible: demoProject.storyBible, graph: demoProject.storyGraph, proposalReady: true,
    onGenerateProposal, onGenerateStoryboard };
  await act(async () => root.render(createElement(BriefPage, briefProps)));
  const proposal = [...host.querySelectorAll("button")].find(button => button.textContent === "生成故事提案")!;
  const storyboard = [...host.querySelectorAll("button")].find(button => button.textContent === "生成可编辑场景与分镜")!;
  expect(proposal.disabled).toBe(true);
  expect(storyboard.disabled).toBe(true);
  await act(async () => { proposal.click(); storyboard.click(); });
  expect(onGenerateProposal).not.toHaveBeenCalled();
  expect(onGenerateStoryboard).not.toHaveBeenCalled();
  await act(async () => root.render(createElement(BriefPage, { ...briefProps, readOnly: false })));
  expect(proposal.disabled).toBe(false);
  expect(storyboard.disabled).toBe(false);
});

it("opens Brief structure and shots by default without changing retained settings or overriding manual collapse", async () => {
  const value = { ...demoProject.brief, decisionPointsPerPath: 3, endingCount: 4, nodeBudget: 16,
    maxOutDegree: 4, desiredJoinCount: 2, shotsPerSceneMin: 2, shotsPerSceneMax: 5, shotCountPolicy: "strict" as const };
  const briefProps = { value, hasSavedProject: true, saving: false,
    onSave: vi.fn(async () => {}), onSaveAndContinue: vi.fn(async () => {}),
    onDraftChange: vi.fn(), onGenerateProposal: vi.fn(async () => {}) };
  await act(async () => root.render(createElement(BriefPage, briefProps)));
  const structure = host.querySelector<HTMLDetailsElement>(".brief-settings details")!;
  expect(structure.querySelector("summary")?.textContent).toBe("剧情结构与分镜");
  expect(structure.open).toBe(true);
  expect([...structure.querySelectorAll("input")].map(input => input.value)).toEqual(["3", "4", "16", "4", "2", "2", "5"]);
  expect(structure.querySelector("select")?.value).toBe("strict");
  expect(host.querySelector<HTMLDetailsElement>(".brief-alternate-workflow details")?.open).toBe(false);
  structure.open = false;
  await act(async () => root.render(createElement(BriefPage, { ...briefProps, saving: true })));
  expect(structure.open).toBe(false);
  structure.open = true;
  expect(structure.querySelector("select")?.value).toBe("strict");
  expect(briefProps.onDraftChange).not.toHaveBeenCalled();
  expect(briefProps.onSave).not.toHaveBeenCalled();
  expect(briefProps.onSaveAndContinue).not.toHaveBeenCalled();
  expect(briefProps.onGenerateProposal).not.toHaveBeenCalled();
});

it("distinguishes a loading cast read from an initial failure and exposes a read-only retry", async () => {
  await renderCast();
  expect(host.textContent).toContain("正在读取角色设定");
  await renderCast(undefined, "network failed");
  expect(host.textContent).toContain("无法读取角色设定");
  expect(host.textContent).not.toContain("正在读取角色设定");
  const retry = host.querySelector("button")!;
  await act(async () => retry.click());
  expect(props.onRefresh).toHaveBeenCalledOnce();
});

it("retains accepted cast on failed refresh but suspends mutations until a successful read", async () => {
  const state: CastReviewState = { status: "accepted", acceptedCast: accepted, candidate: null, staleReasons: [] };
  await renderCast(state, "network failed");
  expect(host.querySelector("h2")?.textContent).toBe("无法刷新角色设定");
  expect(host.textContent).toContain("保留的已确认角色");
  const edit = [...host.querySelectorAll("button")].find(button => button.textContent === "编辑角色设定")!;
  expect(edit.disabled).toBe(true);
  expect(host.textContent).toContain("重试加载角色设定");
  await renderCast(state);
  expect(edit.disabled).toBe(false);
  expect(host.querySelector("h2")?.textContent).toBe("已确认角色设定 r1");
});

it("describes archived Cast preparation as unavailable rather than inviting dispatch", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareCastCandidate");
  await act(async () => root.render(createElement(CastPanel, {
    ...props, readOnly: true, state: { status: "accepted", acceptedCast: accepted, candidate: null, staleReasons: [] },
  })));
  const action = host.querySelector(".cast-next-action")!;
  expect(action.textContent).toContain("此项目为只读，不能准备或发送角色设定任务");
  expect(action.textContent).not.toContain("先准备任务，再发送");
  expect(action.querySelector("button")?.disabled).toBe(true);
  expect(prepare).not.toHaveBeenCalled();
});

it("prepares a character assignment without sending it or confirming a new design", async () => {
  const prepare = vi.spyOn(plotloomApi, "prepareCastCandidate").mockResolvedValue({
    jobId: "prepared-job", expectedCastRevision: 1, binding: accepted.binding, status: "prepared",
    deliveryId: null, manifestHash: null, cast: null, reportAvailable: false,
    createdAt: "2026-10-08T00:00:00Z", deliveredAt: null,
    packagePath: "/qa/package", deliveryPath: "/qa/delivery", assignment: "Frozen QA assignment",
  });
  const send = vi.spyOn(specialistsApi, "send");
  const confirm = vi.spyOn(plotloomApi, "acceptCastCandidate");
  await renderCast({ status: "accepted", acceptedCast: accepted, candidate: null, staleReasons: [] });
  const button = [...host.querySelectorAll("button")].find(item => item.textContent === "准备角色设定任务")!;
  expect(button.disabled).toBe(false);
  await act(async () => button.click());
  expect(prepare).toHaveBeenCalledExactlyOnceWith("project");
  expect(send).not.toHaveBeenCalled();
  expect(confirm).not.toHaveBeenCalled();
  expect(host.querySelector(".cast-assignment textarea")?.textContent).toBe("Frozen QA assignment");
  expect(host.textContent).toContain("已确认角色设定 r1");
});

it("makes a reopened or prepared task prominent rather than claiming its retained result is complete", async () => {
  await renderCast({ status: "reopened", acceptedCast: accepted, candidate: null, staleReasons: [] });
  expect(host.querySelector("h2")?.textContent).toBe("正在编辑角色设定");
  expect(host.textContent).toContain("只有所依据的故事内容与路线未变");
  expect(host.textContent).not.toContain("既有授权");
  expect(host.textContent).toContain("保留的已确认角色");
  await renderCast({ status: "prepared", acceptedCast: accepted, staleReasons: [], candidate: {
    jobId: "new-job", expectedCastRevision: 1, binding: accepted.binding, status: "prepared", cast: null,
    deliveryId: null, manifestHash: null, reportAvailable: false, createdAt: "2026-10-04T00:00:00Z", deliveredAt: null,
  } });
  expect(host.querySelector("h2")?.textContent).toBe("角色任务尚未交付");
  expect(host.querySelector(".reference-state")?.textContent).toBe("任务未交付");
});

it.each(["ready", "prepared"] as const)("labels a stale %s cast candidate as needing an update", async (status) => {
  await renderCast({ status: "stale", acceptedCast: accepted, staleReasons: ["来源已变化"], candidate: {
    jobId: "stale-job", expectedCastRevision: 1, binding: accepted.binding, status,
    cast: status === "ready" ? accepted.cast : null,
    deliveryId: null, manifestHash: null, reportAvailable: false, createdAt: "2026-10-04T00:00:00Z", deliveredAt: null,
  } });
  expect(host.querySelector("h2")?.textContent).toBe("角色设定需重新确认");
  expect(host.querySelector(".reference-state")?.textContent).toBe("需更新");
  const mutation = [...host.querySelectorAll("button")].find(button => button.textContent === (status === "ready" ? "确认使用此角色设定" : "发送给文字创作助手"));
  expect(mutation?.disabled).toBe(true);
});
