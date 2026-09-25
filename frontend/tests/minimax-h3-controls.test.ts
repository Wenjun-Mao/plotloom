import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import type { VideoBackend, VideoBackendProfile } from "../src/types";
import { h3QualifiedDurations, MiniMaxH3DurationField, MiniMaxH3QualityField } from "../src/video-backends/minimax-h3";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const profiles = [1, 8].flatMap((quality) => [
  { id: `q${quality}-portrait`, quality, width: 576, height: 1024 },
  { id: `q${quality}-landscape`, quality, width: 832, height: 480 },
]) as VideoBackendProfile[];

it("switches quality while retaining the selected resolution", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  let chosen = "";
  await act(async () => root.render(createElement(MiniMaxH3QualityField, {
    profiles, value: "q8-landscape", disabled: false, onChange: (value) => { chosen = value; },
  })));
  const select = host.querySelector("select")!;
  expect(select.value).toBe("8");
  await act(async () => { select.value = "1"; select.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(chosen).toBe("q1-landscape");
  await act(async () => root.unmount());
  host.remove();
});

it("shows the full integer request range without claiming playback eligibility", async () => {
  const values = h3QualifiedDurations({ qualifiedDurationSeconds: Array.from({ length: 11 }, (_, index) => index + 5) } as VideoBackend);
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  await act(async () => root.render(createElement(MiniMaxH3DurationField, {
    values, value: 15, disabled: false, onChange: () => {},
  })));
  expect(Array.from(host.querySelectorAll("option")).map((option) => Number(option.value))).toEqual(values);
  expect(host.textContent).toContain("请求秒数不等于实测原片或已审核播放片段时长");
  await act(async () => root.unmount());
  host.remove();
});
