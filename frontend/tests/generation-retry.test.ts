import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { GenerationRetryStatus } from "../src/features/generation-retry/GenerationRetryStatus";
import type { GenerationRetryStatus as Status } from "../src/features/generation-retry/contracts";

const base: Status = { automaticRetryLimit: 1, retryCount: 1, currentJobId: "current-job", currentAttemptId: "current-attempt",
  predecessorJobIds: ["old-job"], state: "exhausted", possiblePriorCost: true };
function render(status: Status) {
  const host = document.createElement("div");
  host.innerHTML = renderToStaticMarkup(createElement(GenerationRetryStatus, { status }));
  return host;
}
it("shows exhausted additional retries and possible cost without claiming a refund", () => {
  const host = render(base);
  expect(host.textContent).toContain("自动重试 1 次，已用 1 次；首次尝试不计入");
  expect(host.textContent).toContain("剩余权限与预算内手动重试");
  expect(host.textContent).toContain("不代表费用已退回");
  expect(host.querySelector("details")?.hasAttribute("open")).toBe(false);
  expect(host.querySelector("details")?.textContent).toContain("old-job");
});
it("does not assign prospective retry authority to a retained record", () => {
  const host = render({ ...base, automaticRetryLimit: null, retryCount: 0, state: "stopped", possiblePriorCost: false });
  expect(host.textContent).toContain("未冻结自动重试额度；不会新增重试授权");
  expect(host.textContent).not.toContain("自动重试 1 次");
  expect(host.textContent).not.toContain("可能已产生费用");
});
