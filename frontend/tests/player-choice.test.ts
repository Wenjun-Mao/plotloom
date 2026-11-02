import { expect, it, vi } from "vitest";

it("opens a route-only choice over the final video frame as soon as playback ends", async () => {
  const story = { gameId: "choice-test", storyRevision: "r1", start: "opening", title: "Test",
    nodes: [
      { id: "opening", title: "Opening", clips: [{ src: "opening.mp4", visibleText: [], dialogue: [] }],
        edges: [{ to: "choose", label: null }] },
      { id: "choose", title: "Decision", clips: [], question: "What now?",
        edges: [{ to: "leave", label: "Leave" }, { to: "stay", label: "Stay" }] },
      { id: "leave", title: "Leave", clips: [], edges: [], ending: { title: "Leave", text: "You left." } },
      { id: "stay", title: "Stay", clips: [], edges: [], ending: { title: "Stay", text: "You stayed." } },
    ] };
  document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
  document.querySelector("#story")!.textContent = JSON.stringify(story);
  const drawImage = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  try {
    await import("../src/player/player");
    document.querySelector<HTMLButtonElement>("button")!.click();
    const video = document.querySelector("video")!;
    Object.defineProperties(video, { ended: { value: true }, readyState: { value: 4 },
      videoWidth: { value: 832 }, videoHeight: { value: 480 } });
    video.dispatchEvent(new Event("ended"));
    const stage = document.querySelector(".choice-stage")!;
    expect(drawImage).toHaveBeenCalledWith(video, 0, 0);
    expect(stage.querySelector("canvas")?.width).toBe(832);
    const choices = stage.querySelectorAll<HTMLButtonElement>("button.choice");
    expect([...choices].map(button => button.textContent)).toEqual(["Leave", "Stay"]);
    choices[1].click();
    expect(document.querySelector(".ending-text")?.textContent).toBe("You stayed.");
    expect([...document.querySelectorAll("header button")].some(button => button.textContent === "结局档案 1/2")).toBe(true);
    const back = [...document.querySelectorAll("button")].find(button => button.textContent === "返回上个选择")!;
    back.click();
    expect(document.querySelector(".choice-stage video")?.getAttribute("src")).toBe("opening.mp4");
  } finally {
    vi.restoreAllMocks();
  }
});

it("keeps ending dialogue visible during its clip and hides it after playback ends", async () => {
  vi.resetModules();
  const story = { format: 1, gameId: "the-last-projection-v3", storyRevision: "r1", assetVersion: "media-v1",
    start: "ending", title: "Test", intro: "", nodes: [
      { id: "ending", title: "Ending", context: "Last scene", text: "", question: "",
        clips: [{ slot: "ending", src: "ending.mp4", durationUnits: 3000, visibleText: [], dialogue: [{ speaker: "A-Lan", text: "我明白了。" }] }],
        edges: [], ending: { title: "Ending", text: "The scene is over." } },
    ] };
  document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
  document.querySelector("#story")!.textContent = JSON.stringify(story);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  try {
    await import("../src/player/player");
    document.querySelector<HTMLButtonElement>("#game button")!.click();
    const shell = document.querySelector(".film-player")!;
    const captions = shell.querySelector<HTMLElement>(".captions")!;
    const video = shell.querySelector("video")!;
    expect(captions.textContent).toContain("A-Lan：我明白了。");
    expect(shell.classList.contains("film-ending")).toBe(false);

    Object.defineProperty(video, "ended", { value: true, configurable: true });
    video.dispatchEvent(new Event("ended"));
    expect(shell.classList.contains("film-ending")).toBe(true);
    expect(captions.textContent).toContain("A-Lan：我明白了。");

    Object.defineProperty(video, "paused", { value: false, configurable: true });
    video.dispatchEvent(new Event("play"));
    expect(shell.classList.contains("film-ending")).toBe(false);
  } finally {
    vi.restoreAllMocks();
  }
});
