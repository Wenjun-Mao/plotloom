import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { AutopilotWorkspace } from "../src/features/autopilot/AutopilotWorkspace";
import { automaticGuidance } from "../src/features/autopilot/guidance";
import { autopilotApi } from "../src/features/autopilot/api";
import { RecommendedWorkflowGuide } from "../src/app/workspace/RecommendedWorkflowGuide";
import { OutlineReport } from "../src/pages/OutlineReport";
import { InstalledProductionSummary } from "../src/pages/InstalledProductionSummary";
import { plotloomApi } from "../src/api";
import { fixtureRun } from "./autopilot-fixture";
import { ProductionPresentationReview } from "../src/pages/ProductionPresentationReview";
import { CastPanel } from "../src/pages/CastPanel";
import type { CastReviewState, ProductionBridgeProposal } from "../src/types";
import { replacementTarget, installedProduction } from "./production-bridge-fixture";
import type { RecommendedWorkflowModel } from "../src/app/workspace/recommendedWorkflow";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());

it.each([false, true])("keeps Storyboard failure/history visible without manual extra (history=%s)", async history => {
  const run = { ...fixtureRun, state: "blocked" as const, phase: history ? "bridge-presentation" : "storyboard",
    checkpoints: [{ operationKey: "storyboard", state: "failed", evidence: { owner: "storyboard", result: {} } },
      ...(history ? [{ operationKey: "storyboard:correction:1", state: "adopted", evidence: { owner: "storyboard", result: {} } }] : [])] };
  vi.spyOn(autopilotApi, "current").mockResolvedValue(run);
  const read = vi.spyOn(autopilotApi, "textFailure").mockResolvedValue({ runId: run.id, runRevision: run.revision,
    stage: "storyboard", stageLabel: "分镜", canRetry: false, reason: "保留原始失败", automaticUsed: 1,
    automaticLimit: 1, terminalContentFailure: true, failedAttemptId: "attempt", rejectionHash: "a".repeat(64),
    issues: [], resolved: history, diagnostics: ["frozen storyboard diagnostic"], history: [{ ordinal: 0, mode: "original", state: "failed", outcome: "failure", comparison: "unknown" }] });
  const retry = vi.spyOn(autopilotApi, "retryText");
  const host = document.createElement("div"), root = createRoot(host); document.body.append(host);
  try {
    await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1,
      readOnly: true, onChanged: async () => undefined, onVideo: vi.fn(), children: createElement("div") })));
    expect(read).toHaveBeenCalledWith("disposable", expect.any(AbortSignal), history ? "storyboard" : undefined);
    const opener = [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "查看问题")!;
    expect(opener).toBeTruthy(); await act(async () => opener.click());
    expect(host.textContent).toContain("frozen storyboard diagnostic");
    expect(host.textContent).toContain("首次生成");
    expect(host.textContent).not.toContain("修改要求后重试");
    expect(retry).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); host.remove(); }
});

it.each([["outline", "故事大纲"], ["characters", "角色设定"], ["art", "美术设定"], ["script", "完整剧本"],
  ["storyboard", "分镜"], ["bridge-intent", "戏剧意图"], ["bridge-presentation", "画面呈现"], ["references", "参考图片"], ["first-frames", "镜头首帧"]])("automatic guidance identifies %s and keeps final review/manual takeover separate", (phase, name) => {
  const text = automaticGuidance({ ...fixtureRun, state: "running", phase }, true)!;
  expect(text).toContain(`当前自动阶段：${name}`); expect(text).toContain("无需手动准备或发送当前任务");
  expect(text).toContain("一次完整人工审阅"); expect(text).toContain("保存手动修改将接管自动运行");
  expect(text).toContain("阅读报告不会确认、接管或发送任务");
});
it("paused, blocked, unknown and manual states do not masquerade as running or human acceptance", () => {
  expect(automaticGuidance({ ...fixtureRun, state: "paused" }, true)).toContain("已暂停");
  expect(automaticGuidance({ ...fixtureRun, state: "blocked" }, true)).toContain("需要处理");
  expect(automaticGuidance(null, false)).toContain("尚待核实");
  expect(automaticGuidance(null, true)).toBeNull();
  expect(automaticGuidance({ ...fixtureRun, state: "taken_over" }, true)).toBeNull();
});

it.each(["ai", "manual", "unknown", "different-hash"])("shared guidance and read-only reports use exact %s provenance without taking over", async kind => {
  const read = vi.spyOn(autopilotApi, "current");
  if (kind === "manual") read.mockResolvedValue(null);
  else if (kind === "unknown") read.mockRejectedValue(new Error("fixture unreadable"));
  else read.mockResolvedValue({ ...fixtureRun, state: "running", phase: "art", checkpoints: [
    { operationKey: "outline", state: "adopted", evidence: { owner: "outline", result: { revision: 3, contentHash: kind === "ai" ? "frozen-outline" : "different" } } },
    { operationKey: "bridge-presentation", state: "adopted", evidence: { owner: "bridge-presentation", result: { revision: 3, contentHash: "bridge-hash" } } },
  ] });
  vi.spyOn(plotloomApi, "reportAvailable").mockResolvedValue(false);
  const write = vi.spyOn(plotloomApi, "patchProject"), start = vi.spyOn(autopilotApi, "start");
  const model: RecommendedWorkflowModel = { currentStep: "source", currentStepLabel: "来源与大纲", nextText: "角色文字已确认，请手动制作图片。",
    steps: [{ id: "source", label: "来源", status: "已确认 r3", adoptedArtifact: { operation: "outline", revision: 3, contentHash: "frozen-outline" } }] };
  const outline = { source: "原始标题", episodes: [{ ep: 1, synopsis: "保留的正文" }] }, before = JSON.stringify(outline);
  const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false,
      onChanged: async () => undefined, onVideo: vi.fn(), children: createElement("div", null,
        createElement(RecommendedWorkflowGuide, { model, actionDisabled: false, onNavigate: vi.fn() }),
        createElement(OutlineReport, { outline, accepted: { revision: 3, contentHash: "frozen-outline" } }),
        createElement(InstalledProductionSummary, { installation: installedProduction({ proposalRevision: 3, proposalContentHash: "bridge-hash" }),
          reviewAcknowledged: true, reviewBasisStatus: "current", disabled: false, canonicalReady: true, onReread: vi.fn() }),
      ) })));
    const guide = host.querySelector('[data-testid="recommended-workflow"]')!;
    if (kind === "manual") expect(guide.textContent).toContain("角色文字已确认，请手动制作图片");
    else { expect(guide.textContent).not.toContain("角色文字已确认"); expect(guide.textContent).toContain(kind === "unknown" ? "尚待核实" : "当前自动阶段：美术设定"); }
    const opener = [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent?.startsWith("阅读"))!;
    expect(opener.disabled).toBe(false);
    expect(opener.textContent).toContain(kind === "ai" ? "AI 已采用" : kind === "manual" ? "已确认" : "来源待核实");
    await act(async () => opener.click());
    expect(host.querySelector("dialog")!.textContent).toContain("只读阅读");
    expect(host.querySelector("dialog")!.querySelectorAll("button")).toHaveLength(1);
    expect(JSON.stringify(outline)).toBe(before); expect(write).not.toHaveBeenCalled(); expect(start).not.toHaveBeenCalled();
    if (kind === "ai") expect(host.querySelector('[data-testid="installed-production"]')!.textContent).toContain("AI 已采用的制作内容");
  } finally { await act(async () => root.unmount()); host.remove(); }
});

it.each(["intent-only", "unknown"])("does not infer presentation adoption or automation from %s evidence", async kind => {
  const read = vi.spyOn(autopilotApi, "current");
  if (kind === "unknown") read.mockRejectedValue(new Error("unreadable"));
  else read.mockResolvedValue({ ...fixtureRun, state: "running", phase: "bridge-presentation", checkpoints: [
    { operationKey: "bridge-intent", state: "adopted", evidence: { owner: "bridge-intent", result: { revision: 3, contentHash: "bridge-hash" } } },
  ] });
  const proposal: ProductionBridgeProposal = { revision: 3, contentHash: "bridge-hash", inputs: {}, replacementTarget: replacementTarget(),
    scenes: [], cuts: [], conflicts: [], advisories: [], installable: false, preparedAt: "now",
    intentPackage: { suggestionOrigin: "none", reviewState: "author_saved", entries: [] },
    presentation: { version: 1, reviewed: false, sourceHash: "source", sources: [], runtimeChoice: { choices: [] }, frozenEvidence: {} } };
  const state: CastReviewState = { status: "accepted", candidate: null, acceptedReviewState: { status: "current", staleReasons: [] }, staleReasons: [],
    acceptedCast: { revision: 1, candidateJobId: "cast-job", binding: { sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "map", graphRevision: 1, graphContentHash: "graph", sectionIds: [] },
      contentHash: "cast", cast: { characters: [] }, consumerMappings: [], reportAvailable: false, differsFromDelivery: null, acceptedAt: "now" } };
  const host = document.createElement("div"), root = createRoot(host);
  try {
    await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: vi.fn(), children: createElement("div", null,
      createElement(ProductionPresentationReview, { projectId: "disposable", proposal, disabled: false, accepted: false, onSave: async () => true, onDirty: vi.fn() }),
      createElement(CastPanel, { projectId: "disposable", state, readOnly: false, loadError: "", onState: vi.fn(), onRefresh: async () => true, onInvalidate: vi.fn(), onTransitionComplete: vi.fn() })) })));
    const presentation = host.querySelector('[data-testid="production-presentation-review"]')!;
    expect(presentation.textContent).not.toContain("AI 已采用的呈现方案");
    if (kind === "unknown") {
      expect(presentation.textContent).toContain("尚待核实"); expect(presentation.textContent).not.toContain("接管自动运行");
      const summary = host.querySelector(".accepted-cast-summary")!;
      expect(summary.textContent).toContain("尚待核实"); expect(summary.textContent).not.toContain("外观参考由自动运行准备");
    } else expect(presentation.textContent).toContain("已采用 · 来源待核实的呈现方案");
  } finally { await act(async () => root.unmount()); }
});
