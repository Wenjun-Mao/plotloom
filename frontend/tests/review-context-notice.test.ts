import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { ArtPanel } from "../src/pages/ArtPanel";
import { CastPanel } from "../src/pages/CastPanel";
import { ReviewContextNotice, reviewContextFailure, reviewContextMessage, reviewContextNextStep } from "../src/pages/ReviewContextNotice";
import type { ReviewContextDiagnostic } from "../src/review-context-types";
import type { ArtReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const source: ReviewContextDiagnostic = { code: "source_context_not_ready", owner: "source", technicalMessage: "an accepted source, outline, current section map, and installed graph are required before preparing cast", field: null };
const characters: ReviewContextDiagnostic = { code: "accepted_cast_not_current", owner: "characters", technicalMessage: "a current accepted cast is required before preparing art", field: null };

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it.each([
  [source, "来源与大纲", "?project=project&stage=source#source"],
  [characters, "角色", "?project=project&stage=characters"],
  [{ code: "art_render_contract_changed", owner: "art", technicalMessage: "unchanged style evidence", field: null }, "美术参考", "?project=project&stage=source#art"],
] as const)("shows typed %s guidance with a separate protected owner link", async (diagnostic, owner, href) => {
  await act(async () => root.render(createElement(ReviewContextNotice, { projectId: "project", diagnostics: [diagnostic] })));
  const notice = host.querySelector(".review-context-notice")!;
  expect(notice.querySelector("ul")?.textContent).toBe(reviewContextMessage(diagnostic));
  const link = notice.querySelector("a")!;
  expect(link.textContent).toBe(`在新页打开${owner}`);
  expect(link.getAttribute("href")).toBe(href);
  expect(link.getAttribute("target")).toBe("_blank");
  const details = notice.querySelector("details")!;
  expect(details.open).toBe(false);
  expect(details.textContent).toContain(diagnostic.technicalMessage);
  expect(details.textContent).toContain(diagnostic.code);
});

it("names changed binding fields without treating their English evidence as UI copy", () => {
  expect(reviewContextMessage({ code: "binding_revision_changed", owner: "characters", field: "cast_revision", technicalMessage: "accepted cast revision changed" })).toBe("角色设定版本已变化，需要重新检查这份设定。");
  expect(reviewContextMessage({ code: "binding_content_changed", owner: "source", field: "graph_content_hash", technicalMessage: "installed graph content changed" })).toBe("已应用故事路线内容已变化，需要重新检查这份设定。");
});

it.each(["art_render_contract_changed", "cast_render_contract_changed"] as const)("does not blame author direction for %s implementation-only invalidation", code => {
  const message = reviewContextMessage({ code, owner: code.startsWith("art") ? "art" : "characters", field: null, technicalMessage: "implementation changed" });
  expect(message).toContain("按当前要求重新审核确认");
  expect(message).not.toMatch(/风格.*已变化|视觉方向.*变化|故事.*变化/);
  expect(reviewContextMessage({ code: "binding_value_changed", owner: "art", field: "render_contract", technicalMessage: "changed" })).toContain("风格、视觉方向与渲染要求");
});

it.each(["binding_revision_changed", "binding_content_changed", "section_context_changed", "art_render_contract_changed"] as const)("keeps %s recovery in the outdated review instead of a prerequisite loop", code => {
  expect(reviewContextNextStep({ code, owner: "source", field: null, technicalMessage: "changed" }, "准备当前设定任务")).toBe("准备当前设定任务");
  expect(reviewContextNextStep(source, "prepare")).toContain("来源与大纲");
  expect(reviewContextNextStep(characters, "prepare")).toContain("角色");
});

it.each([source, characters])("Art's stale guide and disabled continuation follow %s", async diagnostic => {
  vi.spyOn(plotloomApi, "getArt").mockResolvedValue({ acceptedReviewState: { status: "missing", staleReasons: [] }, status: "stale", acceptedArt: null, candidate: null, staleReasons: [diagnostic] });
  const onContinue = vi.fn();
  await act(async () => root.render(createElement(ArtPanel, { projectId: "project", readOnly: false, onContinue })));
  const guide = host.querySelector(".stage-guide")!;
  expect(guide.textContent).toContain(`请先到“${diagnostic.owner === "source" ? "来源与大纲" : "角色"}”`);
  expect(guide.textContent).not.toContain("请更新并确认美术设定");
  const continuation = [...host.querySelectorAll("button")].find(button => button.textContent === "继续：剧本")!;
  expect(continuation.disabled).toBe(true);
  expect(onContinue).not.toHaveBeenCalled();
  expect(host.querySelector(".review-context-notice details")?.textContent).toContain(diagnostic.technicalMessage);
});

it("keeps generic transport failures distinct from typed prerequisite refusals", () => {
  expect(reviewContextFailure(new Error("failed GET"), "fallback")).toBe("failed GET");
  expect(reviewContextFailure(new ApiError("ordinary refusal", 409, { code: "invalid_transition" }), "fallback")).toBe("ordinary refusal");
  expect(reviewContextFailure(new ApiError(source.technicalMessage, 409, { code: "review_context_not_current", diagnostic: source }), "fallback")).toEqual(source);
});

it.each(["art", "cast"] as const)("presents a typed %s preparation refusal rather than raw primary English", async stage => {
  const refusal = new ApiError(source.technicalMessage, 409, { code: "review_context_not_current", diagnostic: source });
  if (stage === "art") {
    vi.spyOn(plotloomApi, "getArt").mockResolvedValue({ acceptedReviewState: { status: "missing", staleReasons: [] }, status: "missing", candidate: null, acceptedArt: null, staleReasons: [] });
    vi.spyOn(plotloomApi, "prepareArtCandidate").mockRejectedValue(refusal);
    await act(async () => root.render(createElement(ArtPanel, { projectId: "project", readOnly: false })));
    const select = host.querySelector<HTMLSelectElement>('select[aria-label="美术风格"]')!;
    await act(async () => { select.value = "realistic"; select.dispatchEvent(new Event("change", { bubbles: true })); });
  } else {
    vi.spyOn(plotloomApi, "prepareCastCandidate").mockRejectedValue(refusal);
    await act(async () => root.render(createElement(CastPanel, { projectId: "project", readOnly: false, state: { acceptedReviewState: { status: "missing", staleReasons: [] }, status: "missing", candidate: null, acceptedCast: null, staleReasons: [] }, loadError: "", onState: vi.fn(), onRefresh: vi.fn(async () => true), onInvalidate: vi.fn(), onTransitionComplete: vi.fn() })));
    const select = host.querySelector<HTMLSelectElement>('select[aria-label="角色图像风格"]')!;
    await act(async () => { select.value = "live-action"; select.dispatchEvent(new Event("change", { bubbles: true })); });
  }
  const prepare = [...host.querySelectorAll("button")].find(button => button.textContent === (stage === "art" ? "准备美术设定任务" : "准备角色设定任务"))!;
  await act(async () => prepare.click());
  const alert = host.querySelector('[role="alert"]')!;
  expect(alert.querySelector("ul")?.textContent).toBe(reviewContextMessage(source));
  expect(alert.querySelector("a")?.textContent).toBe("在新页打开来源与大纲");
  expect(alert.querySelector("details")?.textContent).toContain(source.technicalMessage);
  expect(alert.querySelector("details")?.open).toBe(false);
});

it("dirty Art recovery guidance keeps precedence over an upstream diagnostic", async () => {
  let state: ArtReviewState = { acceptedReviewState: { status: "reopened", staleReasons: [] }, status: "reopened", candidate: null, staleReasons: [], acceptedArt: { revision: 1, candidateJobId: "", contentHash: "hash", binding: {} as NonNullable<ArtReviewState["acceptedArt"]>["binding"], art: { scenes: [], props: [] }, acceptedAt: "2026-10-08T00:00:00Z" } };
  vi.spyOn(plotloomApi, "getArt").mockImplementation(async () => state);
  await act(async () => root.render(createElement(ArtPanel, { projectId: "project", readOnly: false, refreshToken: 1 })));
  const editor = host.querySelector<HTMLTextAreaElement>(".art-json-editor textarea:not(:disabled)")!;
  const dirty = `${editor.value}\n `;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(editor, dirty);
    editor.dispatchEvent(new Event("input", { bubbles: true }));
  });
  state = { ...state, status: "stale", staleReasons: [source], acceptedReviewState: { status: "retained", staleReasons: [source] } };
  await act(async () => root.render(createElement(ArtPanel, { projectId: "project", readOnly: false, refreshToken: 2 })));
  expect(host.querySelector(".stage-guide")?.textContent).toContain("保留了基于旧版本的美术草稿");
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="保留的美术草稿"]')?.value).toBe(dirty);
  expect(host.querySelector(".review-context-notice a")?.textContent).toBe("在新页打开来源与大纲");
});
