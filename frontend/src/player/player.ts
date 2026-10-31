import "./player.css";
import { lastChoicePath, validateSave, type Save, type Story } from "./state";

const story = JSON.parse(document.getElementById("story")!.textContent!) as Story;
const root = document.getElementById("game")!;
const key = `plotloom-game:${story.gameId}`;
let saved: Save | null = null;
let storageUnavailable = false;
let stored: string | null = null;
try { stored = localStorage.getItem(key); } catch { storageUnavailable = true; }
if (stored) {
  try { saved = validateSave(story, JSON.parse(stored)); } catch { /* Malformed progress does not mean storage is denied. */ }
}
let path = [story.start], clip = 0, time = 0, finished = false;
// Keep one media element so a user gesture authorizes sound for subsequent clips.
const video = document.createElement("video");
video.controls = true;
video.playsInline = true;
video.preload = "auto";
const audioKey = `${key}:audio`;
try {
  const audio = JSON.parse(localStorage.getItem(audioKey) ?? "null");
  if (audio && typeof audio.muted === "boolean" && Number.isFinite(audio.volume) && audio.volume >= 0 && audio.volume <= 1) {
    video.volume = audio.volume;
    video.muted = audio.muted;
  }
} catch { /* Keep the browser defaults when preferences are unavailable. */ }
function rememberAudio() {
  try { localStorage.setItem(audioKey, JSON.stringify({ muted: video.muted, volume: video.volume })); }
  catch { /* The element still retains its settings throughout this session. */ }
}
let pausedByUser = false, epoch = 0;

function element<K extends keyof HTMLElementTagNameMap>(tag: K, text = "", className = "") {
  const result = document.createElement(tag);
  result.textContent = text;
  if (className) result.className = className;
  return result;
}
function button(text: string, action: () => void, className = "") {
  const result = element("button", text, className);
  result.type = "button";
  result.onclick = action;
  return result;
}
function save() {
  const value: Save = { revision: story.storyRevision, path: [...path], clip, time, finished };
  saved = value;
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { storageUnavailable = true; showStorageNotice(); }
}
function showStorageNotice() {
  if (!storageUnavailable || root.querySelector(".storage-notice")) return;
  const notice = element("p", "浏览器未允许保存进度。仍可游玩；关闭或刷新后需重新开始。", "storage-notice");
  notice.setAttribute("role", "status");
  root.prepend(notice);
}
function stop() {
  epoch++;
  video.onloadedmetadata = video.onplay = video.onpause = video.onended = video.ontimeupdate = video.onerror = null;
  if (video.hasAttribute("src")) { video.pause(); video.removeAttribute("src"); video.load(); }
}
function title() {
  stop(); root.replaceChildren();
  const panel = element("section", "", "title-card");
  panel.append(element("p", "互动短片", "eyebrow"), element("h1", story.title));
  if (story.intro) panel.append(element("p", story.intro, "intro"));
  panel.append(button("开始", () => { path = [story.start]; clip = time = 0; finished = false; pausedByUser = false; save(); render(); }, "primary"));
  if (saved) panel.append(button("继续", () => { const value = saved!; path = [...value.path]; clip = value.clip; time = value.time; finished = value.finished; pausedByUser = false; render(); }));
  root.append(panel);
  showStorageNotice();
}
function render() {
  stop(); root.replaceChildren();
  const captured = epoch;
  const node = story.nodes.find(node => node.id === path.at(-1))!;
  const shell = element("section", "", "player");
  const top = element("header");
  top.append(element("span", story.title, "game-title"));
  const pause = button("播放", () => {
    pausedByUser = !video.paused;
    if (pausedByUser) video.pause(); else play();
  });
  pause.disabled = !node.clips.length;
  const mute = button("", () => {
    if (video.volume === 0) { video.volume = 1; video.muted = false; } else video.muted = !video.muted;
    updateSoundButton();
    rememberAudio();
  });
  function updateSoundButton() {
    const silent = video.muted || video.volume === 0;
    mute.textContent = silent ? "开启声音" : "静音";
    mute.setAttribute("aria-pressed", String(silent));
  }
  updateSoundButton();
  video.onvolumechange = () => { updateSoundButton(); rememberAudio(); };
  top.append(pause, mute, button("返回标题", () => { if (video.readyState >= 1) time = video.currentTime; save(); title(); }));
  shell.append(top);
  const stage = element("div", "", "stage");
  const caption = element("div", "", "captions");
  const status = element("p", "", "status"); status.setAttribute("role", "status");
  const actions = element("div", "", "actions");
  const current = node.clips[clip];
  function play() {
    void video.play().catch(() => {
      if (epoch === captured && video.paused) { pause.textContent = "播放"; status.textContent = "点击播放以继续。"; }
    });
  }
  if (current) {
    const resumeTime = time;
    video.src = current.src;
    video.setAttribute("aria-label", node.title);
    const active = video;
    const lines = [...current.visibleText, ...current.dialogue.map(line => `${line.speaker ? line.speaker + "：" : ""}${line.text}`)];
    for (const line of lines) caption.append(element("p", line));
    active.onloadedmetadata = () => {
      if (epoch !== captured) return;
      if (resumeTime > 0 && resumeTime < active.duration) active.currentTime = resumeTime;
    };
    let lastSavedSecond = -1;
    active.ontimeupdate = () => { if (epoch !== captured || active.readyState < 1) return; time = active.currentTime; const second = Math.floor(time); if (second !== lastSavedSecond) { lastSavedSecond = second; save(); } };
    active.onplay = () => { if (!active.paused) { pausedByUser = false; pause.textContent = "暂停"; status.textContent = ""; } };
    active.onpause = () => { if (epoch === captured && active.paused) { pause.textContent = "播放"; save(); } };
    active.onerror = () => { status.textContent = "视频无法播放。请确认完整解压了游戏文件。"; };
    active.onended = () => {
      if (epoch !== captured || !active.ended) return;
      if (clip + 1 < node.clips.length) { clip++; time = 0; save(); render(); }
      else { finished = true; save(); showActions(); }
    };
    stage.append(active);
  } else finished = true;
  function move(to: string) { path.push(to); clip = time = 0; finished = false; pausedByUser = false; save(); render(); }
  function showActions() {
    actions.replaceChildren();
    if (node.ending) {
      actions.append(element("h2", node.ending.title), element("p", node.ending.text, "ending-text"));
    } else if (node.edges.some(edge => edge.label !== null)) {
      if (node.question) actions.append(element("h2", node.question));
      for (const edge of node.edges) actions.append(button(edge.label!, () => move(edge.to), "choice"));
    } else if (node.edges.length === 1) {
      actions.append(button("继续", () => move(node.edges[0].to), "primary"));
    }
    if (node.ending) actions.append(button("重新开始", () => { path = [story.start]; clip = time = 0; finished = false; save(); render(); }, "primary"));
    const previous = lastChoicePath(story, path);
    if (previous) actions.append(button("返回上个选择", () => { path = previous; const target = story.nodes.find(item => item.id === path.at(-1))!; clip = Math.max(0, target.clips.length - 1); time = 0; finished = true; save(); render(); }));
    save();
  }
  shell.append(element("p", node.title, "node-title"), stage, caption, status, actions);
  root.append(shell);
  showStorageNotice();
  if (finished) showActions();
  else if (current && !pausedByUser) play();
}
window.addEventListener("pagehide", () => { if (video.readyState >= 1) time = video.currentTime; if (root.querySelector(".player")) { rememberAudio(); save(); } });
title();
