import { expect, it } from "vitest";
import { buildEvidenceBook, buildHandoverBook, readKnowledge, recordKnowledge } from "../src/player/books";
import { recordRoute, readArchive } from "../src/player/archive";
import type { Story } from "../src/player/state";

const story: Story = { format: 1, gameId: "the-last-projection-v3", storyRevision: "r", assetVersion: "a", title: "", intro: "", start: "opening", nodes: [
  { id: "opening", title: "Opening", clips: [], question: "", edges: [{ id: "to-choice", to: "early", label: null }], ending: null },
  { id: "early", title: "First choice", clips: [], question: "First?", edges: [{ id: "watch", to: "watch-memory", label: "Watch" }, { id: "hear", to: "hear-confession", label: "Hear" }], ending: null },
  { id: "watch-memory", title: "Watch", clips: [], question: "", edges: [], ending: null },
  { id: "hear-confession", title: "Hear", clips: [], question: "", edges: [], ending: null },
  { id: "end", title: "Ending", clips: [], question: "", edges: [], ending: { title: "Shared handover", text: "" } },
] };

it("keeps evidence spoiler-safe until the relevant recording or account is completed", () => {
  const partialWatch = buildEvidenceBook(story, ["opening", "early", "watch-memory"], ["opening", "early"]);
  expect(partialWatch.textContent).toContain("未登记的监控卡");
  expect(partialWatch.textContent).not.toContain("火灾当晚的监控");
  expect(partialWatch.textContent).not.toContain("阿岚承认碰倒电暖器");

  const heard = buildEvidenceBook(story, ["opening", "early", "hear-confession"], ["opening", "early", "hear-confession"]);
  expect(heard.textContent).toContain("阿岚承认碰倒电暖器");
  expect(heard.textContent).not.toContain("藏卡半年");

  const watched = buildEvidenceBook(story, ["opening", "early", "watch-memory"], ["opening", "early", "watch-memory"]);
  expect(watched.textContent).toContain("火灾当晚的监控");
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

it("offers explicit return to an archived route while preserving its record", () => {
  const archive = recordRoute(readArchive(story, null), ["opening", "early", "hear-confession", "end"]);
  let fork: string[] | null = null;
  const panel = buildHandoverBook(story, archive, ["opening", "early", "watch-memory"], path => { fork = path; });
  expect(panel.textContent).toContain("已归档路线 · 1");
  expect(panel.textContent).toContain("Hear");
  const replay = [...panel.querySelectorAll("button")].find(button => button.textContent?.includes("回到这条路线最后一次选择"));
  expect(replay).toBeDefined();
  replay!.click();
  expect(fork).toEqual(["opening", "early", "hear-confession", "end"]);
  expect(archive.routes).toHaveLength(1);
});
