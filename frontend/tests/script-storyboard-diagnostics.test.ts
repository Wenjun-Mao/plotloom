import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { ScriptPanel } from "../src/pages/ScriptPanel";
import { StoryboardReviewPanel } from "../src/pages/StoryboardReviewPanel";
import { reviewContextMessage } from "../src/pages/ReviewContextNotice";
import type { ReviewContextDiagnostic } from "../src/review-context-types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

const art: ReviewContextDiagnostic = { code: "accepted_art_not_current", owner: "art", field: null, technicalMessage: "a current accepted art revision is required before preparing script" };
const script: ReviewContextDiagnostic = { code: "accepted_script_not_current", owner: "script", field: null, technicalMessage: "the accepted F4 script context is stale" };
const target: ReviewContextDiagnostic = { code: "binding_value_changed", owner: "brief", field: "target_playthrough_seconds", technicalMessage: "target playthrough seconds changed" };

function setup(stage: "script" | "storyboard", status: "missing" | "stale", diagnostic: ReviewContextDiagnostic) {
  const staleReasons = status === "stale" ? [diagnostic] : [];
  if (stage === "script") {
    vi.spyOn(plotloomApi, "getScript").mockResolvedValue({ status, candidate: null, acceptedScript: null, staleReasons, acceptedReviewState: { status: "missing", staleReasons: [] } });
    return createElement(ScriptPanel, { projectId: "project", readOnly: false, onContinue: vi.fn() });
  }
  vi.spyOn(plotloomApi, "getStoryboardSourceReview").mockResolvedValue({ status, candidate: null, acceptedReview: null, staleReasons, acceptedReviewState: { status: "missing", staleReasons: [] } });
  return createElement(StoryboardReviewPanel, { projectId: "project", readOnly: false, onInstalled: vi.fn() });
}

it.each([
  ["script", art, "美术参考", "?project=project&stage=source#art"],
  ["storyboard", script, "剧本", "?project=project&stage=source#script"],
  ["script", target, "项目简报", "?project=project&stage=brief"],
] as const)("%s stale guidance is readable and preserves technical evidence", async (stage, diagnostic, owner, href) => {
  const panel = setup(stage, "stale", diagnostic);
  await act(async () => root.render(panel));
  const notice = host.querySelector(".review-context-notice")!;
  expect(notice.querySelector("ul")?.textContent).toBe(reviewContextMessage(diagnostic));
  expect(notice.querySelector("a")?.textContent).toBe(`在新页打开${owner}`);
  expect(notice.querySelector("a")?.getAttribute("href")).toBe(href);
  expect(notice.querySelector("a")?.getAttribute("target")).toBe("_blank");
  expect(notice.querySelector("details")?.open).toBe(false);
  expect(notice.querySelector("details")?.textContent).toContain(diagnostic.technicalMessage);
  const guide = host.querySelector(".stage-guide")!;
  expect(guide.textContent).not.toContain(diagnostic.technicalMessage);
  if (diagnostic === target) expect(guide.textContent).toContain("请按当前审核要求重新准备并确认剧本");
  else expect(guide.textContent).toContain(`请先到“${owner}”`);
  if (stage === "script") expect([...host.querySelectorAll("button")].find(button => button.textContent === "继续：分镜评审")?.disabled).toBe(true);
});

it.each(["script", "storyboard"] as const)("%s preparation shows typed refusal without an English primary error", async stage => {
  const diagnostic = stage === "script" ? art : script;
  const panel = setup(stage, "missing", diagnostic);
  const refusal = new ApiError(diagnostic.technicalMessage, 409, { code: "review_context_not_current", diagnostic });
  vi.spyOn(plotloomApi, stage === "script" ? "prepareScriptCandidate" : "prepareStoryboardSourceReviewCandidate").mockRejectedValue(refusal);
  await act(async () => root.render(panel));
  const button = [...host.querySelectorAll("button")].find(item => item.textContent === (stage === "script" ? "准备剧本任务" : "准备分镜任务"))!;
  await act(async () => button.click());
  const notice = host.querySelector('[role="alert"]')!;
  expect(notice.querySelector("ul")?.textContent).toBe(reviewContextMessage(diagnostic));
  expect(notice.querySelector("details")?.open).toBe(false);
  expect(notice.querySelector("details")?.textContent).toContain(diagnostic.technicalMessage);
  expect(button.disabled).toBe(false);
});
