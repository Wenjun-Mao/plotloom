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
let path = [story.start], clip = 0, time = 0, finished = false, muted = false;
let video: HTMLVideoElement | null = null;
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
function stop() { epoch++; if (video) { video.pause(); video.removeAttribute("src"); video.load(); } video = null; }
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
  const pause = button(pausedByUser || finished || !node.clips.length ? "播放" : "暂停", () => {
    if (!video) return;
    pausedByUser = !video.paused;
    pause.textContent = pausedByUser ? "播放" : "暂停";
    if (video) { if (pausedByUser) video.pause(); else void video.play().catch(() => { status.textContent = "点击播放以继续"; }); }
  });
  pause.disabled = !node.clips.length;
  const mute = button(muted ? "开启声音" : "静音", () => { muted = !muted; if (video) video.muted = muted; mute.textContent = muted ? "开启声音" : "静音"; mute.setAttribute("aria-pressed", String(muted)); });
  mute.setAttribute("aria-pressed", String(muted));
  top.append(pause, mute, button("返回标题", () => { time = video?.currentTime || time; save(); title(); }));
  shell.append(top);
  const stage = element("div", "", "stage");
  const caption = element("div", "", "captions");
  const status = element("p", "", "status"); status.setAttribute("role", "status");
  const actions = element("div", "", "actions");
  const current = node.clips[clip];
  if (current) {
    video = element("video"); video.src = current.src; video.playsInline = true; video.muted = muted; video.preload = "auto";
    video.setAttribute("aria-label", node.title);
    video.controls = true;
    const active = video;
    const lines = [...current.visibleText, ...current.dialogue.map(line => `${line.speaker ? line.speaker + "：" : ""}${line.text}`)];
    for (const line of lines) caption.append(element("p", line));
    active.onloadedmetadata = () => {
      if (epoch !== captured) return;
      if (time > 0 && time < active.duration) active.currentTime = time;
      if (!finished && !pausedByUser) void active.play().catch(() => { status.textContent = "点击视频的播放按钮以继续。"; });
    };
    let lastSavedSecond = -1;
    active.ontimeupdate = () => { if (epoch !== captured) return; time = active.currentTime; const second = Math.floor(time); if (second !== lastSavedSecond) { lastSavedSecond = second; save(); } };
    active.onplay = () => { pausedByUser = false; pause.textContent = "暂停"; status.textContent = ""; };
    active.onpause = () => { if (epoch === captured) { pause.textContent = "播放"; save(); } };
    active.onerror = () => { status.textContent = "视频无法播放。请确认完整解压了游戏文件。"; };
    active.onended = () => {
      if (epoch !== captured) return;
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
}
window.addEventListener("pagehide", () => { if (video) time = video.currentTime; if (root.querySelector(".player")) save(); });
title();
