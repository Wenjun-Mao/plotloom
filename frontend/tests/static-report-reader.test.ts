import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { StaticReportReader } from "../src/components/StaticReportReader";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it.each([
  ["script", "剧本", "场次与台词已完整展开", "折叠、复制和导出按钮"],
  ["storyboard", "分镜", "分段与提示词已完整展开", "复制、导出和图片放大功能"],
] as const)("names the original %s report and preserves its admitted static boundary", async (kind, subject, contents, disabled) => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const url = `/api/v2/projects/qa/${kind}/candidates/frozen/report?presentation=static`;
  const admission = vi.spyOn(plotloomApi, "admitReportRead").mockResolvedValue({ complete: vi.fn(), cancel: vi.fn() });
  try {
    await act(async () => root.render(createElement(StaticReportReader, { kind, url })));
    expect(host.querySelector("summary")?.textContent).toBe(`阅读原始${subject}报告（只读）`);
    expect(host.textContent).toContain("原始报告的只读展示");
    expect(host.textContent).toContain(`不会随当前${subject}修改`);
    expect(host.textContent).toContain(contents);
    expect(host.textContent).toContain(disabled);
    expect(host.textContent).not.toContain("上游脚本");
    expect(host.textContent).toContain("所有分支的时长相加，不等于一次从开场到结局的播放时长");
    const frame = host.querySelector("iframe")!;
    expect(frame.title).toBe(`原始${subject}交付报告（只读）`);
    expect(frame.getAttribute("src")).toBe(url);
    expect(frame.getAttribute("sandbox")).toBe("");
    expect(frame.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(admission).toHaveBeenCalledWith(url, expect.any(AbortSignal));
    expect(host.querySelector("button")).toBeNull();
  } finally {
    await act(async () => root.unmount());
    host.remove();
    vi.restoreAllMocks();
  }
});

it("enlarges the admitted frozen report, restores focus and closes across report/view changes", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const url = "/api/v2/projects/qa/storyboard/candidates/first/report?presentation=static";
  const cancel = vi.fn();
  const admission = vi.spyOn(plotloomApi, "admitReportRead").mockResolvedValue({ complete: vi.fn(), cancel });
  vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function (this: HTMLDialogElement) {
    this.open = false; this.dispatchEvent(new Event("close"));
  });
  const render = async (nextUrl = url, active = true) => act(async () => root.render(createElement(StaticReportReader, { kind: "storyboard", url: nextUrl, expandable: true, active })));
  const open = async () => act(async () => host.querySelector<HTMLButtonElement>(".static-report-toolbar button")!.click());
  try {
    await render(); await open();
    const dialog = host.querySelector("dialog")!;
    expect(dialog.open).toBe(true);
    expect(dialog.getAttribute("aria-labelledby")).toBe(dialog.querySelector("h2")!.id);
    expect(dialog.textContent).toContain("阅读或关闭不会确认、修改方案或生成媒体");
    const frame = dialog.querySelector("iframe")!;
    expect(frame.src).toContain(url);
    expect(frame.title).toBe("原始分镜交付报告（放大只读）");
    expect(frame.getAttribute("sandbox")).toBe("");
    expect(frame.getAttribute("referrerpolicy")).toBe("no-referrer");
    await act(async () => dialog.querySelector<HTMLButtonElement>("button")!.click());
    expect(host.querySelector("dialog")).toBeNull();
    expect(document.activeElement).toBe(host.querySelector(".static-report-toolbar button"));
    await open();
    const outside = document.createElement("button"); host.append(outside); outside.focus();
    await render(url, false);
    expect(host.querySelector("dialog")).toBeNull();
    expect(document.activeElement).toBe(outside);
    outside.remove();
    await render();
    expect(host.querySelector("dialog")).toBeNull();
    await open();
    const nextUrl = url.replace("first", "second");
    await render(nextUrl);
    expect(host.querySelector("dialog")).toBeNull();
    expect(host.querySelector("iframe")!.getAttribute("src")).toBe(nextUrl);
    expect(admission).toHaveBeenCalledWith(nextUrl, expect.any(AbortSignal));
    expect(cancel).toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  }
});
