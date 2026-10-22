import { act, createElement, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { plotloomApi, PlotloomApiClient } from "../src/api";
import { ProjectReportFrame } from "../src/components/ProjectReportFrame";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const url = "/api/v2/projects/p/script/candidates/one/report";

it("StrictMode and queued owner invalidation mount only the admitted real URL; cleanup cannot settle a later frame", async () => {
  const client = new PlotloomApiClient(vi.fn() as unknown as typeof fetch);
  const admission = vi.spyOn(plotloomApi, "admitReportRead").mockImplementation((path, signal) => client.admitReportRead(path, signal));
  const host = document.createElement("div"), root = createRoot(host);
  const paused = client.suspendProjectReads("p");
  try {
    await act(async () => root.render(createElement(StrictMode, null, createElement(ProjectReportFrame, { url, title: "original report", sandbox: "" }))));
    expect(host.querySelector("iframe")).toBeNull();
    const nextUrl = url.replace("one", "two");
    await act(async () => root.render(createElement(StrictMode, null, createElement(ProjectReportFrame, { url: nextUrl, title: "original report", sandbox: "" }))));
    await act(async () => paused.resume());
    const frame = host.querySelector("iframe")!;
    expect(frame.getAttribute("src")).toBe(nextUrl); expect(frame.hasAttribute("srcdoc")).toBe(false);
    expect(frame.getAttribute("sandbox")).toBe("");
    const closing = client.suspendProjectReads("p"); let result: boolean | undefined;
    const settling = closing.settle().then(value => { result = value; });
    await act(async () => root.render(null)); await settling;
    expect(result).toBe(false); closing.resume();
    await act(async () => root.render(createElement(ProjectReportFrame, { url, title: "original report", sandbox: "" })));
    const current = host.querySelector("iframe")!, again = client.suspendProjectReads("p"); let done = false;
    const waiting = again.settle().then(value => { done = value; });
    frame.dispatchEvent(new Event("load")); await Promise.resolve(); expect(done).toBe(false);
    await act(async () => current.dispatchEvent(new Event("load"))); await waiting;
    expect(done).toBe(true); again.resume();
  } finally { paused.resume(); await act(async () => root.unmount()); admission.mockRestore(); }
});
