import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { contentLanguageApi } from "../src/features/content-language/api";
import { useContentLanguageCheck } from "../src/features/content-language/useContentLanguageCheck";
import { ContentLanguageReview } from "../src/features/content-language/ContentLanguageReview";
import { LanguageTaskObserver } from "../src/features/content-language/LanguageTaskObserver";
import type { ContentLanguageStage, ContentLanguageStatus } from "../src/features/content-language/contracts";
import { languagePass, languageRequired } from "./content-language-fixture";
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const button = (name: string) => [...host.querySelectorAll("button")].find(button => button.textContent === name)!;
const original = { lang: "en", entries: [{ id: "hero", prose: "The keeper leaves.", providerTechnical: "English instructions.", literalText: "再见" }] };
function Host({ stage = "art", value = original, basis = "source-one", jobId = "candidate" }: { stage?: ContentLanguageStage; value?: Record<string, unknown>; basis?: string; jobId?: string }) {
  const check = useContentLanguageCheck({ projectId: "project", stage, jobId, candidate: value, original, basis });
  return createElement("div", null, createElement(ContentLanguageReview, { check }), createElement("button", { disabled: !check.ready }, "采用当前完整候选"));
}
const render = async (props: Parameters<typeof Host>[0] = {}) => act(async () => root.render(createElement(Host, props)));
const checkCurrent = async () => act(async () => button("检查当前完整候选语言").click());
const renderAndCheck = async (props: Parameters<typeof Host>[0] = {}) => { await render(props); await checkCurrent(); };
beforeEach(() => {
  vi.spyOn(contentLanguageApi, "status").mockImplementation(async (_project, _stage, job) => languageRequired(job)); host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });
it.each(["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"] as const)("checks the entire submitted %s candidate before enabling adoption", async stage => {
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(languagePass()); await renderAndCheck({ stage });
  expect(check).toHaveBeenCalledExactlyOnceWith("project", stage, "candidate", original, 1);
  expect(button("采用当前完整候选").disabled).toBe(false); expect(host.textContent).toContain("AI 语言检查可能遗漏问题");
});
it("a structural completion or uncertain/failed checker cannot become a language pass", async () => {
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue({ ...languagePass(), state: "running", verdict: null });
  await renderAndCheck(); expect(button("采用当前完整候选").disabled).toBe(true);
  check.mockResolvedValue({ ...languagePass(), state: "failed", verdict: null }); await renderAndCheck({ basis: "source-two" });
  expect(button("采用当前完整候选").disabled).toBe(true); expect(host.textContent).toContain("原语言检查执行失败");
  expect(host.textContent).not.toContain("当前候选存在内容语言问题");
});
it("an edited complete candidate invalidates the original pass immediately and is never silently translated", async () => {
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(languagePass()); await renderAndCheck();
  const edited = { ...original, entries: [{ ...original.entries[0], prose: "她决定离开。" }] };
  await render({ value: edited }); expect(button("采用当前完整候选").disabled).toBe(true); expect(check).toHaveBeenCalledTimes(1);
  await act(async () => button("检查当前完整候选语言").click());
  expect(check).toHaveBeenLastCalledWith("project", "art", "candidate", edited, 1); expect(edited.entries[0].prose).toBe("她决定离开。");
});
it("rejection displays trusted field paths and exact Unicode span text without turning explanations into directions", async () => {
  vi.spyOn(contentLanguageApi, "check").mockResolvedValue({ ...languagePass(), verdict: "reject", blocker: "请修正候选中的语言问题。",
    findings: [{ code: "wrong_language", span: { path: "$.entries[0].prose", start: 1, end: 3, text: "😀她" }, explanation: "这段普通创作 prose 使用了错误的项目语言。" }],
    issues: [{ code: "content_language_mismatch", fieldPaths: ["$.entries[0].prose"], repairFacts: { contentLocale: "en-US" } }] });
  await renderAndCheck(); expect(host.querySelector("blockquote")?.textContent).toBe("😀她"); expect(host.textContent).toContain("$.entries[0].prose");
  expect(button("采用当前完整候选").disabled).toBe(true); expect(contentLanguageApi.check).toHaveBeenCalledTimes(1);
});
it("UNKNOWN checks are observed by exact check ID without admitting another operation", async () => {
  const unknown = { ...languagePass(), state: "outcome_unknown" as const, verdict: null };
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(unknown);
  const reconcile = vi.spyOn(contentLanguageApi, "reconcile").mockResolvedValue(unknown); await renderAndCheck();
  await act(async () => button("核对原语言检查").click());
  expect(check).toHaveBeenCalledTimes(1); expect(reconcile).toHaveBeenCalledExactlyOnceWith("project", unknown.checkJobId);
  expect(button("采用当前完整候选").disabled).toBe(true);
});
it("late language pass cannot authorize a different candidate or source basis", async () => {
  let resolve!: (status: ContentLanguageStatus) => void;
  vi.spyOn(contentLanguageApi, "check").mockReturnValueOnce(new Promise(done => { resolve = done; })).mockResolvedValue({ ...languagePass("next"), verdict: "uncertain" });
  await renderAndCheck(); await renderAndCheck({ jobId: "next", basis: "new-source" }); await act(async () => resolve(languagePass()));
  expect(button("采用当前完整候选").disabled).toBe(true); expect(host.textContent).toContain("助手无法确认当前内容语言");
});
it("a checker observation for a different check ID is refused", async () => {
  vi.spyOn(contentLanguageApi, "check").mockResolvedValue({ ...languagePass(), state: "running", verdict: null });
  vi.spyOn(contentLanguageApi, "reconcile").mockResolvedValue({ ...languagePass(), checkJobId: "other" });
  await renderAndCheck(); vi.useFakeTimers(); await act(async () => vi.advanceTimersByTimeAsync(3000));
  expect(button("采用当前完整候选").disabled).toBe(true);
});
it("native delivery and checker verdict stay separate; original checker reject never calls receive/adopt", async () => {
  const verified = vi.fn(), continued = vi.fn();
  const reject = { ...languagePass(), verdict: "reject" as const };
  vi.spyOn(contentLanguageApi, "reconcile").mockResolvedValue(reject);
  await act(async () => root.render(createElement(LanguageTaskObserver, { projectId: "project", initial: reject, disabled: false, onVerified: verified, onContinue: continued })));
  expect(host.textContent).toContain("当前候选存在内容语言问题"); expect(verified).not.toHaveBeenCalled(); expect(continued).not.toHaveBeenCalled();
});

it("opening and reopening read frozen retry authority without posting or resetting it", async () => {
  const frozen = { ...languagePass(), retry: { retryCount: 1, automaticRetryLimit: 3, currentJobId: "local-current", currentAttemptId: "attempt-current", predecessorJobIds: ["local-prior"], state: "ready" as const, possiblePriorCost: true } };
  vi.mocked(contentLanguageApi.status).mockResolvedValue(frozen);
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(frozen);
  await render();
  expect(check).not.toHaveBeenCalled(); expect(host.querySelector('input[type="number"]')).toBeNull();
  expect(host.textContent).toContain("已冻结自动重试 3 次，已用 1 次"); expect(host.textContent).toContain("local-current");
  expect(host.textContent).toContain("attempt-current"); expect(host.textContent).toContain("可能已产生费用");
  expect(button("采用当前完整候选").disabled).toBe(true);
  await checkCurrent(); expect(check).toHaveBeenCalledExactlyOnceWith("project", "art", "candidate", original, 3);
  await act(async () => root.unmount()); root = createRoot(host); await render();
  expect(check).toHaveBeenCalledTimes(1); expect(host.textContent).toContain("已冻结自动重试 3 次");
});
it("new explicit checks freeze a valid prospective allowance; invalid or negative counts cannot dispatch", async () => {
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(languagePass());
  await render(); expect(check).not.toHaveBeenCalled();
  const field = host.querySelector<HTMLInputElement>('input[type="number"]')!;
  expect(field.value).toBe("1");
  const change = async (value: string) => act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
  for (const invalid of ["-1", "1.5", ""]) { await change(invalid); await checkCurrent(); expect(check).not.toHaveBeenCalled(); }
  await change("0"); await checkCurrent();
  expect(check).toHaveBeenCalledExactlyOnceWith("project", "art", "candidate", original, 0);
});
it("pending retry observation retains its original checker and never resubmits from the browser", async () => {
  const pending = { ...languagePass(), state: "outcome_unknown" as const, verdict: null,
    retry: { retryCount: 1, automaticRetryLimit: 1, currentJobId: "local-next", currentAttemptId: "attempt-next", predecessorJobIds: ["local-first"], state: "retry_pending" as const, possiblePriorCost: true } };
  vi.mocked(contentLanguageApi.status).mockResolvedValue(pending);
  const check = vi.spyOn(contentLanguageApi, "check");
  const reconcile = vi.spyOn(contentLanguageApi, "reconcile").mockResolvedValue(pending);
  await render(); await act(async () => button("核对原语言检查").click());
  expect(reconcile).toHaveBeenCalledExactlyOnceWith("project", "check-original"); expect(check).not.toHaveBeenCalled();
  expect(host.textContent).toContain("核对状态不会重新提交"); expect(button("采用当前完整候选").disabled).toBe(true);
});
it("a legacy check with no frozen allowance never receives a new default retry grant", async () => {
  vi.mocked(contentLanguageApi.status).mockResolvedValue(languagePass());
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue(languagePass());
  await render(); expect(host.textContent).toContain("未冻结自动重试额度"); await checkCurrent();
  expect(check).toHaveBeenCalledExactlyOnceWith("project", "art", "candidate", original, undefined);
});

it("capacity-deferred prepared checks continue only through an explicit original-intent action", async () => {
  const prepared = { ...languagePass(), state: "spawn_intent" as const, verdict: null,
    retry: { retryCount: 0, automaticRetryLimit: 2, currentJobId: "local-original", currentAttemptId: "attempt-original", predecessorJobIds: [], state: "ready" as const, possiblePriorCost: false } };
  vi.mocked(contentLanguageApi.status).mockResolvedValue(prepared);
  const check = vi.spyOn(contentLanguageApi, "check").mockResolvedValue({ ...prepared, state: "running" });
  await render(); expect(check).not.toHaveBeenCalled();
  await act(async () => button("继续当前检查").click());
  expect(check).toHaveBeenCalledExactlyOnceWith("project", "art", "candidate", undefined, 2);
  expect(button("采用当前完整候选").disabled).toBe(true);
});
