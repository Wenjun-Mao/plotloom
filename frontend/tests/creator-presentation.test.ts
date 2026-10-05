import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Button, Field } from "../src/components";
import { CastPanel } from "../src/pages/CastPanel";
import { BriefPage } from "../src/pages/BriefPage";
import { QuarantinePage } from "../src/pages/QuarantinePage";
import { demoProject } from "../src/demo";
import { specialistsApi } from "../src/features/specialists/api";
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
  consumerMappings: [],
  binding: { sourceRevision: 1, sourceContentHash: "b", outlineRevision: 1, outlineContentHash: "c", sectionMapRevision: 1, sectionMapContentHash: "d", graphRevision: 1, graphContentHash: "e", sectionIds: ["opening"] },
};
const props = { projectId: "project", readOnly: false, loadError: "", onState: vi.fn(), onRefresh: vi.fn(async () => true), onInvalidate: vi.fn(), onTransitionComplete: vi.fn() };
async function renderCast(state?: CastReviewState, loadError = "") {
  await act(async () => root.render(createElement(CastPanel, { ...props, state, loadError })));
}

it("marks required labels inline without giving optional inputs a native validation constraint", async () => {
  await act(async () => root.render(createElement(Field, { label: "故事内容", required: true, children: createElement("textarea", { "aria-required": true }) })));
  expect(host.querySelector("label > span")?.textContent).toBe("故事内容 *");
  expect(host.querySelector(".required-mark")?.getAttribute("aria-hidden")).toBe("true");
  expect(host.querySelector("textarea")?.hasAttribute("required")).toBe(false);
  expect(host.querySelector("textarea")?.getAttribute("aria-required")).toBe("true");
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
  expect(host.textContent).not.toContain("所有阶段输出都已通过合同验证");
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
  const structure = host.querySelector<HTMLDetailsElement>(".brief-layout details")!;
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
  expect(host.textContent).toContain("保留的已接受角色");
  const edit = [...host.querySelectorAll("button")].find(button => button.textContent === "编辑角色设定")!;
  expect(edit.disabled).toBe(true);
  expect(host.textContent).toContain("重试加载角色设定");
  await renderCast(state);
  expect(edit.disabled).toBe(false);
  expect(host.querySelector("h2")?.textContent).toBe("已接受角色设定 r1");
});

it("makes a reopened or prepared task prominent rather than claiming its retained result is complete", async () => {
  await renderCast({ status: "reopened", acceptedCast: accepted, candidate: null, staleReasons: [] });
  expect(host.querySelector("h2")?.textContent).toBe("角色设定修订轮次已打开");
  expect(host.textContent).toContain("保留的已接受角色");
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
  expect(host.querySelector("h2")?.textContent).toBe("上下文已过期");
  expect(host.querySelector(".reference-state")?.textContent).toBe("需更新");
  const mutation = [...host.querySelectorAll("button")].find(button => button.textContent === (status === "ready" ? "确认使用此角色设定" : "发送给文字创作助手"));
  expect(mutation?.disabled).toBe(true);
});
