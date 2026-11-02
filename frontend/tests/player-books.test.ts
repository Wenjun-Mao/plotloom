import { expect, it } from "vitest";
import { buildEvidenceBook, buildHandoverBook, readKnowledge, recordKnowledge } from "../src/player/books";
import { recordRoute, readArchive } from "../src/player/archive";
import type { Story } from "../src/player/state";

const story: Story = { format: 1, gameId: "the-last-projection-v3", storyRevision: "r", assetVersion: "a", title: "", intro: "", start: "opening", nodes: [
  { id: "opening", title: "Opening", clips: [], question: "", edges: [{ id: "to-choice", to: "early", label: null }], ending: null },
  { id: "early", title: "First choice", clips: [], question: "First?", edges: [{ id: "watch", to: "watch-memory", label: "Watch" }, { id: "hear", to: "hear-confession", label: "Hear" }], ending: null },
  { id: "watch-memory", title: "Watch", clips: [], question: "", edges: [{ id: "to-second", to: "watch-second", label: null }], ending: null },
  { id: "watch-second", title: "Second choice", clips: [], question: "Second?", edges: [{ id: "end-a-edge", to: "end-a", label: "First ending" }, { id: "end-b-edge", to: "end-b", label: "Second ending" }], ending: null },
  { id: "hear-confession", title: "Hear", clips: [], question: "", edges: [{ id: "hear-end", to: "end-a", label: "Confess ending" }], ending: null },
  { id: "hear-n10", title: "Explanation", clips: [], question: "", edges: [], ending: null },
  { id: "end-a", title: "Ending A", clips: [], question: "", edges: [], ending: { title: "Shared handover", text: "" } },
  { id: "end-b", title: "Ending B", clips: [], question: "", edges: [], ending: { title: "Quiet handover", text: "" } },
] };

it("keeps evidence spoiler-safe until the relevant recording or account is completed", () => {
  const partialWatch = buildEvidenceBook(story, ["opening", "early", "watch-memory"], ["opening", "early"]);
  expect(partialWatch.textContent).toContain("未登记的监控卡");
  expect(partialWatch.textContent).not.toContain("火灾当晚的监控");
  expect(partialWatch.textContent).not.toContain("阿岚承认碰倒电暖器");

  const heard = buildEvidenceBook(story, ["opening", "early", "hear-confession"], ["opening", "early", "hear-confession"]);
  expect(heard.textContent).toContain("阿岚承认碰倒电暖器");
  expect(heard.textContent).toContain("她承认那晚碰倒了电暖器。");
  expect(heard.textContent).not.toContain("以为火已经灭了");
  expect(heard.textContent).not.toContain("藏卡半年");

  const watched = buildEvidenceBook(story, ["opening", "early", "watch-memory"], ["opening", "early", "watch-memory"]);
  expect(watched.textContent).toContain("火灾当晚的监控");
});

it("reveals the belief about the fire only after the later explanation, including after reload", () => {
  let knowledge = recordKnowledge(readKnowledge(story, null), "hear-confession", true);
  let panel = buildEvidenceBook(story, knowledge.entered, knowledge.completed);
  expect(panel.textContent).toContain("她承认那晚碰倒了电暖器。");
  expect(panel.textContent).not.toContain("以为火已经灭了");

  knowledge = recordKnowledge(knowledge, "hear-n10", true);
  knowledge = readKnowledge(story, JSON.parse(JSON.stringify(knowledge)));
  panel = buildEvidenceBook(story, knowledge.entered, knowledge.completed);
  expect(panel.textContent).toContain("她补充说，当时以为火已经灭了。");
});

it("recomputes encountered and completed beats when a book opens after playback", () => {
  const entered = recordKnowledge(readKnowledge(story, null), "watch-memory");
  const duringClip = buildEvidenceBook(story, entered.entered, entered.completed).textContent;
  const afterPlayback = recordKnowledge(entered, "watch-memory", true);
  const after = buildEvidenceBook(story, afterPlayback.entered, afterPlayback.completed).textContent;
  expect(duringClip).not.toContain("火灾当晚的监控");
  expect(after).toContain("火灾当晚的监控");
});

it("retains completed discoveries after abandoning and reloading an unfinished route", () => {
  const discovered = recordKnowledge(readKnowledge(story, null), "watch-memory", true);
  const reloaded = readKnowledge(story, JSON.parse(JSON.stringify(discovered)));
  const panel = buildEvidenceBook(story, reloaded.entered, reloaded.completed);
  expect(panel.textContent).toContain("火灾当晚的监控");
  expect(panel.textContent).not.toContain("藏卡半年");
  const abandonedCurrentPath = ["opening", "early"];
  expect(abandonedCurrentPath).not.toContain("watch-memory");
  expect(reloaded.completed).toContain("watch-memory");
});

it("offers deliberate return to the current unresolved opening choice without navigating while browsing", () => {
  let returned: string[] | null = null;
  const panel = buildHandoverBook(story, readArchive(story, null), ["opening", "early"], path => { returned = path; });
  const resume = [...panel.querySelectorAll("button")].find(button => button.textContent === "回到这个选择");
  expect(resume).toBeDefined();
  expect(returned).toBeNull();
  resume!.click();
  expect(returned).toEqual(["opening", "early"]);
});

it("offers explicit return to every encountered choice on an archived route while preserving its record", () => {
  const archivedPath = ["opening", "early", "watch-memory", "watch-second", "end-a"];
  const archive = recordRoute(readArchive(story, null), archivedPath);
  let fork: string[] | null = null;
  const panel = buildHandoverBook(story, archive, ["opening", "early", "hear-confession"], path => { fork = path; });
  expect(panel.textContent).toContain("已归档路线 · 1");
  const replay = [...panel.querySelectorAll("button")].filter(button => button.textContent?.startsWith("回到路线 1"));
  expect(replay).toHaveLength(2);
  replay[0].click();
  expect(fork).toEqual(["opening", "early"]);
  replay[1].click();
  expect(fork).toEqual(["opening", "early", "watch-memory", "watch-second"]);
  expect(archive.routes).toHaveLength(1);
});
