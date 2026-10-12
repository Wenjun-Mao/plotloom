import { act, createElement, Fragment } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it } from "vitest";
import { ScriptContentReview, ScriptDraftEpisodeReview } from "../src/features/graph/ScriptContentReview";
import type { ScriptBinding } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

const binding = {
  sectionBindings: [{ sectionId: "opening", episode: 2 }, { sectionId: "ending", episode: 9 }],
  completeRouteSectionIds: [["opening", "ending"]], routeOnlySectionIds: ["choice"],
} as ScriptBinding;

it("reads candidate and accepted content through their own exact bindings and keeps stored order and occurrences", async () => {
  const repeatedScene = {
    sceneId: "S-重复", lighting: "琥珀灯光", characters: ["阮星"], props: ["断裂应急杆"],
    flow: [{ action: `第一步\n${"她用带手套的右手检查控制台，确认两条线路互斥。".repeat(10)}` },
      { speaker: "阮星", line: `安迪，\n${"我会把选择权还给你。".repeat(12)}`, delivery: "压低声音" }],
  };
  const candidate = { episodes: [{ ep: 9, targetSeconds: 37, scenes: [repeatedScene, structuredClone(repeatedScene)] }, { ep: 2, targetSeconds: 51, scenes: [repeatedScene] }] };
  const acceptedBinding = { ...binding, sectionBindings: [{ sectionId: "opening", episode: 7 }], routeOnlySectionIds: [] } as ScriptBinding;
  const accepted = { episodes: [{ ep: 7, scenes: [{ ...repeatedScene, sceneId: "S-已确认" }] }] };
  await act(async () => root.render(createElement(Fragment, null,
    createElement(ScriptContentReview, { title: "待审阅候选 · 未确认", statusDescription: "候选状态 ready，不分配已确认版本号。", script: candidate, binding }),
    createElement(ScriptContentReview, { title: "当前已确认剧本 r4", script: accepted, binding: acceptedBinding }),
  )));

  const candidateView = host.querySelector<HTMLElement>('[aria-label="待审阅候选 · 未确认"]')!;
  const acceptedView = host.querySelector<HTMLElement>('[aria-label="当前已确认剧本 r4"]')!;
  expect([...candidateView.querySelectorAll("[data-script-section]")].map(item => item.getAttribute("data-script-section"))).toEqual(["ending", "opening"]);
  expect(candidateView.querySelector('[data-script-section="ending"]')?.getAttribute("data-script-episode")).toBe("9");
  expect(candidateView.querySelectorAll('[data-script-occurrence="ending:9:1"], [data-script-occurrence="ending:9:2"]')).toHaveLength(2);
  expect(acceptedView.querySelector('[data-script-section="opening"]')?.getAttribute("data-script-episode")).toBe("7");
  expect(candidateView.textContent).toContain("此对象的冻结绑定");
  expect(candidateView.textContent).toContain("章节计划画面时长 37 秒");
  expect(candidateView.textContent).toContain("互斥结局不会合计");
  expect(candidateView.textContent).toContain("阮星：安迪");
  expect(candidateView.textContent).toContain("压低声音");
  expect(candidateView.querySelector("script")).toBeNull();
  expect(candidateView.textContent).toContain("她用带手套的右手检查控制台");
  expect(candidateView.textContent).toContain("我会把选择权还给你。");
  expect(candidateView.textContent).toContain("候选状态 ready，不分配已确认版本号。");
});

it("keeps route-only nodes as controls and surfaces ambiguous or missing frozen bindings", async () => {
  const routeOnly = { episodes: [] };
  await act(async () => root.render(createElement(ScriptContentReview, { title: "路线控制候选", script: routeOnly, binding: { sectionBindings: [], completeRouteSectionIds: [], routeOnlySectionIds: ["choice"] } as unknown as ScriptBinding })));
  expect(host.querySelector('[data-script-episode]')).toBeNull();
  expect(host.textContent).toContain("choice · 本对象的冻结绑定明确标为仅控制路线");
  await act(async () => root.render(createElement(ScriptContentReview, { title: "不完整候选", script: { episodes: [{ ep: 2, scenes: [] }, { ep: 2, scenes: [] }] }, binding: { sectionBindings: [{ sectionId: "opening", episode: 2 }, { sectionId: "missing", episode: 4 }], completeRouteSectionIds: [], routeOnlySectionIds: [] } as unknown as ScriptBinding })));
  expect(host.textContent).toContain("不唯一或缺失");
  expect(host.textContent).toContain("episode 4 在原始剧本中缺失");
  expect(host.querySelectorAll(".script-content-mismatch").length).toBeGreaterThanOrEqual(3);
  expect(host.textContent).toContain("查看此对象的冻结绑定与完整原始剧本 JSON");
});

it("renders an edited episode only against the retained base binding and preserves invalid draft JSON", async () => {
  const episode = { ep: 2, scenes: [{ sceneId: "S-草稿", characters: [], flow: [{ action: "已修改动作" }] }] };
  await act(async () => root.render(createElement(ScriptDraftEpisodeReview, { title: "未保存的章节草稿 · 基于 r4", text: JSON.stringify(episode), binding, sectionId: "opening" })));
  expect(host.querySelector('[data-script-section="opening"]')?.getAttribute("data-script-episode")).toBe("2");
  expect(host.textContent).toContain("已修改动作");
  await act(async () => root.render(createElement(ScriptDraftEpisodeReview, { title: "保留草稿", text: JSON.stringify({ ...episode, ep: 99 }), binding, sectionId: "opening" })));
  expect(host.textContent).toContain("无法按基准绑定阅读");
  expect(host.textContent).toContain('{"ep":99');
});
