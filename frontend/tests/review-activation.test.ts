import { act, createElement, StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useReviewActivation } from "../src/pages/useReviewActivation";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

function deferred() {
  let resolve!: (success: boolean) => void;
  const promise = new Promise<boolean>(done => { resolve = done; });
  return { promise, resolve };
}

function Probe({ load }: { load: () => Promise<boolean> }) {
  const { checking, failed, recheck } = useReviewActivation({ projectId: "same-project", active: true, refreshToken: 1, load });
  return createElement("div", null,
    createElement("output", null, checking ? "checking" : failed ? "failed" : "current"),
    createElement("button", { onClick: () => void recheck() }, "recheck"),
  );
}

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("does not let an older StrictMode initial verdict replace a newer successful read", async () => {
  const first = deferred();
  const latest = deferred();
  const load = vi.fn().mockReturnValueOnce(first.promise).mockReturnValue(latest.promise);
  await act(async () => root.render(createElement(StrictMode, null, createElement(Probe, { load }))));
  expect(load).toHaveBeenCalledTimes(2);
  await act(async () => { latest.resolve(true); await latest.promise; });
  expect(host.querySelector("output")?.textContent).toBe("current");
  await act(async () => { first.resolve(false); await first.promise; });
  expect(host.querySelector("output")?.textContent).toBe("current");
});

it("keeps the newer failed verdict when an older overlapping retry succeeds later", async () => {
  const first = deferred();
  const latest = deferred();
  const load = vi.fn().mockReturnValueOnce(first.promise).mockReturnValue(latest.promise);
  await act(async () => root.render(createElement(Probe, { load })));
  await act(async () => host.querySelector("button")?.click());
  await act(async () => { latest.resolve(false); await latest.promise; });
  expect(host.querySelector("output")?.textContent).toBe("failed");
  await act(async () => { first.resolve(true); await first.promise; });
  expect(host.querySelector("output")?.textContent).toBe("failed");
});
