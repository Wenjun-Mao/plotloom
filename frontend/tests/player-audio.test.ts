import { expect, it, vi } from "vitest";

it("keeps the native sound setting across clips and synchronizes the game button", async () => {
  const key = "plotloom-game:sound-test:audio";
  const story = { gameId: "sound-test", storyRevision: "r1", start: "opening", title: "Sound test",
    nodes: [{ id: "opening", title: "Opening", edges: [], clips: ["first", "second"].map(slot =>
      ({ slot, src: slot + ".mp4", dialogue: [], visibleText: [] })) }] };
  document.body.innerHTML = '<main id="game"></main><script id="story" type="application/json"></script>';
  document.querySelector("#story")!.textContent = JSON.stringify(story);
  localStorage.setItem(key, JSON.stringify({ muted: true, volume: .5 }));
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  try {
    await import("../src/player/player");
    document.querySelector("button")!.click();
    const video = document.querySelector("video")!;
    expect(play).toHaveBeenCalledOnce();
    expect(video.muted).toBe(true);
    expect(video.volume).toBe(.5);

    // The native speaker button and slider change these media properties.
    video.muted = false;
    video.volume = .35;
    video.dispatchEvent(new Event("volumechange"));
    expect(document.querySelector('[aria-pressed="false"]')?.textContent).toBe("静音");
    Object.defineProperty(video, "ended", { configurable: true, value: true });
    video.dispatchEvent(new Event("ended"));
    expect(document.querySelector("video")).toBe(video);
    expect(video.getAttribute("src")).toBe("second.mp4");
    expect(video.volume).toBe(.35);
    expect(video.muted).toBe(false);

    document.querySelector<HTMLButtonElement>('[aria-pressed="false"]')!.click();
    expect(video.muted).toBe(true);
    expect(JSON.parse(localStorage.getItem(key)!)).toEqual({ muted: true, volume: .35 });
    video.volume = 0;
    document.querySelector<HTMLButtonElement>('[aria-pressed="true"]')!.click();
    expect(video.muted).toBe(false);
    expect(video.volume).toBeGreaterThan(0);
  } finally {
    vi.restoreAllMocks();
  }
});
