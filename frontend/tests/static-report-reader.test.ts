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
