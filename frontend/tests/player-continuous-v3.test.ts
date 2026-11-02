import { expect, it, vi } from "vitest";

const story = { format: 1, gameId: "the-last-projection-v3", storyRevision: "r1", assetVersion: "media-v1",
  start: "opening", title: "Test", intro: "", nodes: [
    { id: "opening", title: "开袋之前", context: "第一章", text: "", question: "", clips: [{ slot: "opening", src: "opening.mp4", durationUnits: 1000, visibleText: [], dialogue: [] }], edges: [{ id: "open", to: "early", label: null }], ending: null },
    { id: "early", title: "先留下什么？", context: "第一章", text: "", question: "先做什么？", clips: [], edges: [{ id: "watch", to: "watch-memory", label: "先看完整监控，让画面说话" }, { id: "hear", to: "hear", label: "先听阿岚说" }], ending: null },
    { id: "watch-memory", title: "先看那一晚", context: "第二章", text: "", question: "", clips: [{ slot: "watch-memory", src: "watch-memory.mp4", durationUnits: 1000, visibleText: ["完整监控"], dialogue: [] }], edges: [{ id: "watch-first", to: "watch-second", label: null }], ending: null },
    { id: "watch-second", title: "口供", context: "第二章", text: "", question: "", clips: [{ slot: "watch-second", src: "watch-second.mp4", durationUnits: 1000, visibleText: [], dialogue: [] }], edges: [{ id: "wait", to: "watch-context", label: null }], ending: null },
    { id: "watch-context", title: "空着的放映位", context: "第二章", text: "这段只留给你阅读。", question: "", clips: [], edges: [{ id: "finish", to: "ending", label: null }], ending: null },
    { id: "ending", title: "共同交接", context: "第三章", text: "", question: "", clips: [{ slot: "ending", src: "ending.mp4", durationUnits: 1000, visibleText: [], dialogue: [] }], edges: [], ending: { title: "共同交接", text: "交接完成。" } },
    { id: "hear", title: "阿岚先开口", context: "第二章", text: "", question: "", clips: [], edges: [], ending: null },
  ] };

function mockMedia() {
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
}
function finish(video: HTMLVideoElement) {
  Object.defineProperty(video, "ended", { value: true, configurable: true });
  video.dispatchEvent(new Event("ended"));
}
async function start() {
  vi.resetModules(); localStorage.clear(); document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
  document.querySelector("#story")!.textContent = JSON.stringify(story);
  mockMedia(); await import("../src/player/player");
  document.querySelector<HTMLButtonElement>('#game button')!.click();
}

it("advances a V3 film cut naturally, waits on text, and settles at the ending", async () => {
  try {
    await start();
    finish(document.querySelector("video")!);
    const openingChoice = document.querySelector<HTMLElement>(".choice-stage")!;
    expect(openingChoice.classList.contains("v3-frame")).toBe(true);
    expect(openingChoice.hasAttribute("style")).toBe(false);
    const progressFill = document.querySelector<HTMLElement>(".progress-fill")!;
    expect(progressFill.classList.contains("step-1-of-3")).toBe(true);
    expect(progressFill.hasAttribute("style")).toBe(false);
    const watch = [...document.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "先看完整监控，让画面说话")!;
    watch.click();
    const memory = document.querySelector("video")!;
    expect(memory.getAttribute("src")).toBe("watch-memory.mp4");
    expect(memory.controls).toBe(true);
    expect([...document.querySelectorAll<HTMLButtonElement>(".film-hud button")].map(button => button.textContent)).toEqual(["声音", "返回标题"]);
    expect(document.querySelector(".journal")).toBeNull();

    finish(memory);
    expect(document.querySelector(".save-status")?.textContent).toBe("存档位置 · 口供");
    const second = document.querySelector("video")!;
    expect(second.getAttribute("src")).toBe("watch-second.mp4");
    // Old media events cannot advance a second time after its handler is retired.
    Object.defineProperty(second, "ended", { value: false, configurable: true });
    memory.dispatchEvent(new Event("ended"));
    expect(document.querySelector(".save-status")?.textContent).toBe("存档位置 · 口供");

    finish(second);
    expect(document.querySelector(".save-status")?.textContent).toBe("存档位置 · 空着的放映位");
    expect(document.querySelector(".choice-stage video")?.getAttribute("src")).toBe("watch-second.mp4");
    expect([...document.querySelectorAll<HTMLButtonElement>(".actions button")].map(button => button.textContent)).toEqual(["进入下一幕"]);
    document.querySelector<HTMLButtonElement>(".actions button")!.click();
    expect(document.querySelector("video")?.getAttribute("src")).toBe("ending.mp4");
    finish(document.querySelector("video")!);
    expect(document.querySelector(".ending-text")?.textContent).toBe("交接完成。");
    expect([...document.querySelectorAll(".actions button")].map(button => button.textContent)).toEqual(["重新开始"]);
  } finally { vi.restoreAllMocks(); }
});

it("continues an older finished watch-memory save directly to its successor", async () => {
  try {
    vi.resetModules(); localStorage.clear(); document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
    document.querySelector("#story")!.textContent = JSON.stringify(story);
    localStorage.setItem("plotloom-game:the-last-projection-v3", JSON.stringify({ revision: "r1", path: ["opening", "early", "watch-memory"], clip: 0, time: 1, finished: true }));
    mockMedia(); await import("../src/player/player");
    [...document.querySelectorAll<HTMLButtonElement>("#game button")].find(button => button.textContent === "继续")!.click();
    expect(document.querySelector(".save-status")?.textContent).toBe("存档位置 · 口供");
    expect(document.querySelector("video")?.getAttribute("src")).toBe("watch-second.mp4");
  } finally { vi.restoreAllMocks(); }
});

it("offers playback recovery only for a browser autoplay block and removes it once play succeeds", async () => {
  try {
    vi.resetModules(); localStorage.clear(); document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
    document.querySelector("#story")!.textContent = JSON.stringify(story);
    mockMedia();
    vi.spyOn(HTMLMediaElement.prototype, "play").mockRejectedValueOnce(new DOMException("blocked", "NotAllowedError")).mockResolvedValue();
    await import("../src/player/player");
    document.querySelector<HTMLButtonElement>('#game button')!.click();
    await Promise.resolve(); await Promise.resolve();
    const recovery = document.querySelector<HTMLButtonElement>(".playback-recovery")!;
    expect(recovery.textContent).toBe("点击播放以继续");
    const video = document.querySelector<HTMLVideoElement>("video")!;
    Object.defineProperty(video, "paused", { value: false, configurable: true });
    video.dispatchEvent(new Event("play"));
    expect(document.querySelector(".playback-recovery")).toBeNull();
    expect(document.querySelector(".status")?.textContent).toBe("");
  } finally { vi.restoreAllMocks(); }
});

it("does not present unrelated media failures as browser autoplay blocks", async () => {
  try {
    vi.resetModules(); localStorage.clear(); document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
    document.querySelector("#story")!.textContent = JSON.stringify(story);
    mockMedia(); vi.spyOn(HTMLMediaElement.prototype, "play").mockRejectedValueOnce(new Error("decode failure"));
    await import("../src/player/player");
    document.querySelector<HTMLButtonElement>('#game button')!.click();
    await Promise.resolve(); await Promise.resolve();
    expect(document.querySelector(".playback-recovery")).toBeNull();
    expect(document.querySelector(".status")?.textContent).toBe("视频暂时无法播放。");
  } finally { vi.restoreAllMocks(); }
});


it.each(["watch", "hear"])("continues an old %s callback save into the held Chapter 3 decision", async route => {
  try {
    vi.resetModules(); localStorage.clear();
    const film = { ...story.nodes[2], id: "opening", edges: [{ id: "recap", to: `${route}-callback`, label: null }] };
    const recap = { ...story.nodes[4], id: `${route}-callback`, title: "把决定留在自己手里", text: `${route} route recap`, edges: [{ id: "decide", to: `${route}-c01`, label: null }] };
    const choice = { ...story.nodes[1], id: `${route}-c01`, context: "第三章", edges: [{ id: "end", to: "ending", label: "交接" }] };
    const fixture = { ...story, nodes: [film, recap, choice, story.nodes[5]] };
    document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
    document.querySelector("#story")!.textContent = JSON.stringify(fixture);
    localStorage.setItem("plotloom-game:the-last-projection-v3", JSON.stringify({ revision: "r1", path: ["opening", recap.id], clip: 0, time: 0, finished: true }));
    mockMedia(); await import("../src/player/player");
    [...document.querySelectorAll<HTMLButtonElement>("button")].find(b => b.textContent === "继续")!.click();
    expect(document.querySelector(".choice-overlay")?.textContent).toContain("交接");
    expect(document.querySelector(".decision-recap p")?.textContent).toBe(recap.text);
    expect(document.querySelector(".decision-recap")?.hasAttribute("open")).toBe(false);
    expect(document.querySelector(".chapter-progress")?.textContent).toContain("第三章");
    expect(document.querySelector(".choice-stage video")?.getAttribute("src")).toBe("watch-memory.mp4");
    const save = JSON.parse(localStorage.getItem("plotloom-game:the-last-projection-v3")!);
    expect(save.path).toEqual(["opening", recap.id, choice.id]);
    expect(document.querySelector(".actions")?.textContent).not.toContain("进入下一幕");
    document.querySelector<HTMLButtonElement>(".choice-overlay button")!.click();
    expect(JSON.parse(localStorage.getItem("plotloom-game:the-last-projection-v3")!).path.at(-1)).toBe("ending");
  } finally { vi.restoreAllMocks(); }
});
