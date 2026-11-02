import "./player.css";
import { lastChoicePath, logicalPosition, validateSave, type Save, type Story } from "./state";
import { journal, readArchive, recordRoute } from "./archive";
import { buildEvidenceBook, buildHandoverBook, readKnowledge, recordKnowledge } from "./books";

const story = JSON.parse(document.getElementById("story")!.textContent!) as Story;
const root = document.getElementById("game")!;
const key = `plotloom-game:${story.gameId}`;
const isV3 = story.gameId === "the-last-projection-v3";
if (isV3) root.classList.add("v3-mode");
let saved: Save | null = null;
let storageUnavailable = false;
let stored: string | null = null;
try { stored = localStorage.getItem(key); } catch { storageUnavailable = true; }
if (stored) {
  try { saved = validateSave(story, JSON.parse(stored)); } catch { /* Malformed progress does not mean storage is denied. */ }
}
let path = [story.start], clip = 0, time = 0, finished = false;
let archive = readArchive(story, null);
try { archive = readArchive(story, JSON.parse(localStorage.getItem(`${key}:archive`) ?? "null")); } catch { /* Session play remains available. */ }
let knowledge = readKnowledge(story, null);
if (isV3) try { knowledge = readKnowledge(story, JSON.parse(localStorage.getItem(`${key}:knowledge`) ?? "null")); } catch { /* Session play remains available. */ }
function rememberKnowledge(nodeId: string, completed = false) {
  if (!isV3) return;
  knowledge = recordKnowledge(knowledge, nodeId, completed);
  try { localStorage.setItem(`${key}:knowledge`, JSON.stringify(knowledge)); }
  catch { storageUnavailable = true; showStorageNotice(); }
}
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
  const current = story.nodes.find(node => node.id === path.at(-1))?.clips[clip];
  const position = logicalPosition(current, time);
  const value: Save = { revision: story.storyRevision, path: [...path], clip, time, finished, ...(position ? { position } : {}) };
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
  if (saved) {
    const node = story.nodes.find(node => node.id === saved!.path.at(-1))!;
    panel.append(element("p", `已保存 · ${node.title}${saved.finished ? " · 已抵达" : ` · ${Math.floor(saved.time)} 秒`}`, "saved-position"));
    panel.append(button("继续", () => { const value = saved!; path = [...value.path]; clip = value.clip; time = value.time; finished = value.finished; pausedByUser = false; render(); }));
  }
  panel.append(collection());
  root.append(panel);
  showStorageNotice();
}
function discovery() {
  const endings = story.nodes.filter(node => node.ending);
  const seen = new Set(archive.routes.map(route => route.ending));
  return { total: new Set(endings.map(node => node.ending!.title)).size,
    found: new Set(endings.filter(node => seen.has(node.id)).map(node => node.ending!.title)).size };
}
function collection() {
  const section = element("section", "", "collection");
  const seen = new Set(archive.routes.map(route => route.ending));
  const endings = story.nodes.filter(node => node.ending);
  // Explicit structural branches may share the same authored ending.
  const titles = new Set(endings.map(node => node.ending!.title));
  const found = new Set(endings.filter(node => seen.has(node.id)).map(node => node.ending!.title));
  section.append(element("h2", `结局档案 · ${found.size}/${titles.size}`));
  for (const name of titles) section.append(element("p", found.has(name) ? `已发现 · ${name}` : "未发现 · 待开启的胶片"));
  if (archive.routes.length) {
    const retained = element("details"); retained.append(element("summary", `保留路线 · ${archive.routes.length}`));
    for (const route of archive.routes) {
      const ending = story.nodes.find(node => node.id === route.ending)!;
      retained.append(element("p", `${journal(story, route.path).map(item => item.label).join(" → ")} → ${ending.ending!.title}`));
    }
    section.append(retained);
  }
  return section;
}
function lastFrame(src: string) {
  if (video.getAttribute("src") === src && video.ended && video.readyState >= 2) {
    const canvas = element("canvas");
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (context && canvas.width && canvas.height) {
      context.drawImage(video, 0, 0);
      return canvas;
    }
  }
  // Continue or backtracking may reach the choice without a decoded frame in memory.
  const still = element("video");
  still.muted = true; still.playsInline = true; still.preload = "auto";
  still.onloadedmetadata = () => {
    if (!isV3 && still.videoHeight) still.parentElement?.style.setProperty("--frame-ratio", String(still.videoWidth / still.videoHeight));
    if (Number.isFinite(still.duration)) still.currentTime = Math.max(0, still.duration - 0.5 / 24);
  };
  still.src = src;
  return still;
}

function render() {
  const node = story.nodes.find(node => node.id === path.at(-1))!;
  // Older V3 saves can record a fully watched film node before its new
  // continuous successor rule was applied. Continue from that proven end.
  if (isV3 && finished && node.clips.length && node.edges.length === 1 && node.edges[0].label === null) {
    move(node.edges[0].to); return;
  }
  // The two route recaps introduce the decision; retain their graph/save identity
  // while presenting their words alongside the following choice.
  if (isV3 && ["watch-callback", "hear-callback"].includes(node.id) && node.edges.length === 1) {
    rememberKnowledge(node.id, true);
    move(node.edges[0].to); return;
  }
  rememberKnowledge(node.id);
  const hasChoices = node.edges.some(edge => edge.label !== null);
  const choosing = hasChoices && (finished || !node.clips.length);
  const reading = isV3 && ["watch-context", "hear-context"].includes(node.id);
  const recap = isV3 && ["watch-c01", "hear-c01"].includes(node.id)
    ? story.nodes.find(item => item.id === node.id.replace("c01", "callback")) : undefined;
  const source = (choosing || reading) && path.slice().reverse()
    .map(id => story.nodes.find(item => item.id === id)?.clips.at(-1)).find(Boolean);
  const frame = source ? lastFrame(source.src) : null;
  stop(); root.replaceChildren();
  const captured = epoch;
  const shell = element("section", "", "player");
  if (isV3) {
    shell.classList.add("film-player");
    if (node.ending && finished) shell.classList.add("film-ending");
  }
  const top = element("header");
  if (isV3) top.className = "film-hud";
  top.append(element("span", story.title, "game-title"));
  const pause = button("播放", () => {
    pausedByUser = !video.paused;
    if (pausedByUser) video.pause(); else play();
  });
  pause.hidden = choosing;
  pause.disabled = !node.clips.length;
  const mute = button("", () => {
    if (video.volume === 0) { video.volume = 1; video.muted = false; } else video.muted = !video.muted;
    updateSoundButton();
    rememberAudio();
  });
  if (isV3) mute.className = "sound-trigger";
  function updateSoundButton() {
    const silent = video.muted || video.volume === 0;
    mute.textContent = isV3 ? "声音" : silent ? "开启声音" : "静音";
    mute.setAttribute("aria-pressed", String(silent));
    mute.setAttribute("aria-label", silent ? "开启声音" : "关闭声音");
  }
  updateSoundButton();
  video.onvolumechange = () => { updateSoundButton(); rememberAudio(); };
  if (isV3) top.append(mute, button("返回标题", () => { if (video.readyState >= 1) time = video.currentTime; save(); title(); }));
  else top.append(pause, mute, button("返回标题", () => { if (video.readyState >= 1) time = video.currentTime; save(); title(); }));
  const discoveries = discovery();
  const archiveButton = button(`结局档案 ${discoveries.found}/${discoveries.total}`, () => {
    const open = shell.querySelector(".in-play-archive");
    if (open) { open.remove(); archiveButton.setAttribute("aria-expanded", "false"); }
    else { const panel = collection(); panel.classList.add("in-play-archive"); shell.append(panel); archiveButton.setAttribute("aria-expanded", "true"); panel.scrollIntoView({ block: "nearest" }); }
  });
  archiveButton.setAttribute("aria-expanded", "false");
  if (isV3) {
    const openBook = (kind: "evidence" | "handover", opener: HTMLButtonElement) => {
      const wasPlaying = !video.paused && !choosing;
      if (video.readyState >= 1) time = video.currentTime;
      save();
      video.pause();
      const dialog = document.createElement("dialog");
      dialog.className = "book-dialog";
      const close = button("合上", () => dialog.close());
      close.className = "book-close";
      const content = kind === "evidence"
        ? buildEvidenceBook(story, knowledge.entered, knowledge.completed)
        : buildHandoverBook(story, archive, path, returnToChoice);
      dialog.append(close, content);
      dialog.addEventListener("close", () => {
        dialog.remove();
        if (wasPlaying) play();
        opener.focus();
      }, { once: true });
      shell.append(dialog);
      dialog.showModal();
      close.focus();
    };
    const evidenceButton = button("物证册", () => openBook("evidence", evidenceButton));
    const handoverButton = button("交接簿", () => openBook("handover", handoverButton));
    evidenceButton.className = handoverButton.className = "book-trigger";
    const bookDock = element("nav", "", "book-dock");
    bookDock.setAttribute("aria-label", "故事记录");
    bookDock.append(evidenceButton, handoverButton);
    shell.append(bookDock);
  } else top.append(archiveButton);
  shell.append(top);
  if (isV3) {
    const chapters = [...new Set(story.nodes.map(item => item.context).filter((value): value is string => !!value))];
    const chapter = node.context ?? chapters[0] ?? "";
    const chapterIndex = Math.max(0, chapters.indexOf(chapter));
    const progress = element("div", "", "chapter-progress");
    progress.setAttribute("role", "progressbar");
    progress.setAttribute("aria-valuemin", "1");
    progress.setAttribute("aria-valuemax", String(chapters.length));
    progress.setAttribute("aria-valuenow", String(chapterIndex + 1));
    progress.setAttribute("aria-label", `故事进度：第 ${chapterIndex + 1} 章，共 ${chapters.length} 章`);
    progress.append(element("span", chapter.split("/ ").at(-1) ?? ""));
    const track = element("span", "", "progress-track");
    const fill = element("span", "", "progress-fill");
    fill.classList.add(`step-${chapterIndex + 1}-of-${chapters.length}`);
    track.append(fill); progress.append(track); shell.append(progress);
  }
  shell.append(element("p", `存档位置 · ${node.title}`, "save-status"));
  shell.append(element("p", node.context || "旧影院 / 交接前夜", "eyebrow"));
  const stage = element("div", "", choosing || reading ? "stage choice-stage" : "stage");
  if (isV3 && frame) stage.classList.add("v3-frame");
  if (reading) shell.classList.add("reading-pause");
  if (frame) {
    if (!isV3 && frame instanceof HTMLCanvasElement) stage.style.setProperty("--frame-ratio", String(frame.width / frame.height));
    frame.setAttribute("aria-hidden", "true"); stage.append(frame);
  }
  const caption = element("div", "", "captions");
  const status = element("p", "", "status"); status.setAttribute("role", "status");
  const actions = element("div", "", "actions");
  const current = node.clips[clip];
  function play() {
    void video.play().catch((error: unknown) => {
      if (epoch !== captured || !video.paused) return;
      const blocked = typeof error === "object" && error !== null && "name" in error && error.name === "NotAllowedError";
      if (isV3 && blocked) {
        actions.replaceChildren(button("点击播放以继续", play, "primary playback-recovery"));
        status.textContent = "浏览器已阻止自动播放。";
      } else if (isV3) {
        if (!video.error) status.textContent = "视频暂时无法播放。";
      } else { pause.textContent = "播放"; status.textContent = "点击播放以继续。"; }
    });
  }
  if (current && !choosing) {
    const resumeTime = time;
    video.src = current.src;
    video.setAttribute("aria-label", node.title);
    const active = video;
    function updateCaptions() {
      const segment = current.segments?.slice().reverse().find(item => active.currentTime >= item.start) ?? current;
      const lines = [...segment.visibleText, ...segment.dialogue.map(line => `${line.speaker ? line.speaker + "：" : ""}${line.text}`)];
      const text = lines.join("\n");
      if (caption.textContent !== text) caption.textContent = text;
    }
    updateCaptions();
    active.onloadedmetadata = () => {
      if (epoch !== captured) return;
      if (resumeTime > 0) active.currentTime = Math.min(resumeTime, Math.max(0, active.duration - .1));
    };
    let lastSavedSecond = -1;
    active.ontimeupdate = () => { if (epoch !== captured || active.readyState < 1) return; time = active.currentTime; updateCaptions(); const second = Math.floor(time); if (second !== lastSavedSecond) { lastSavedSecond = second; save(); } };
    active.onplay = () => {
      if (!active.paused) {
        shell.classList.remove("film-ending"); pausedByUser = false; pause.textContent = "暂停"; status.textContent = "";
        actions.querySelector(".playback-recovery")?.remove();
      }
    };
    active.onpause = () => { if (epoch === captured && active.paused) { pause.textContent = "播放"; save(); } };
    active.onerror = () => { status.textContent = "视频无法播放。请确认完整解压了游戏文件。"; };
    active.onended = () => {
      if (epoch !== captured || !active.ended) return;
      if (clip + 1 < node.clips.length) { clip++; time = 0; save(); render(); }
      else if (isV3 && node.edges.length === 1 && node.edges[0].label === null) {
        rememberKnowledge(node.id, true);
        move(node.edges[0].to);
      }
      else { finished = true; rememberKnowledge(node.id, true); save(); showActions(); }
    };
    stage.append(active);
  } else finished = true;
  function move(to: string) { path.push(to); clip = time = 0; finished = false; pausedByUser = false; save(); render(); }
  function returnToChoice(choicePath: string[]) {
    const choice = story.nodes.find(item => item.id === choicePath.at(-1));
    if (!choice?.edges.some(edge => edge.label !== null)) return;
    path = [...choicePath]; clip = Math.max(0, choice.clips.length - 1);
    time = 0; finished = true; pausedByUser = true; save(); render();
  }
  function showActions() {
    actions.replaceChildren();
    if (node.ending) {
      shell.classList.add("film-ending");
      actions.classList.add("ending-actions");
      archive = recordRoute(archive, path);
      const updatedDiscovery = discovery();
      archiveButton.textContent = `结局档案 ${updatedDiscovery.found}/${updatedDiscovery.total}`;
      try { localStorage.setItem(`${key}:archive`, JSON.stringify(archive)); } catch { storageUnavailable = true; showStorageNotice(); }
      actions.append(element("h2", node.ending.title), element("p", node.ending.text, "ending-text"));
      const decisions = journal(story, path).map(entry => entry.label);
      if (decisions.length) actions.append(element("p", `这一夜，我选择：${decisions.join(" → ")}`, "ending-decision"));
      actions.append(collection());
    } else if (hasChoices) {
      if (!choosing) { render(); return; }
      const overlay = element("div", "", "choice-overlay");
      overlay.append(element("h2", node.question || node.title));
      for (const edge of node.edges) overlay.append(button(edge.label!, () => move(edge.to), "choice"));
      stage.append(overlay);
    } else if (node.edges.length === 1) {
      const next = story.nodes.find(item => item.id === node.edges[0].to);
      if (isV3 && !current && node.edges[0].label === null) {
        actions.append(button("进入下一幕", () => move(node.edges[0].to), "primary"));
      } else if (current && next && !next.clips.length && next.edges.some(edge => edge.label !== null)) {
        move(next.id); return;
      }
      else if (!isV3) actions.append(button("继续", () => move(node.edges[0].to), "primary"));
    }
    if (node.ending) actions.append(button("重新开始", () => { path = [story.start]; clip = time = 0; finished = false; save(); render(); }, "primary"));
    const previous = isV3 ? null : lastChoicePath(story, path);
    if (previous) actions.append(button("返回上个选择", () => { path = previous; const target = story.nodes.find(item => item.id === path.at(-1))!; clip = Math.max(0, target.clips.length - 1); time = 0; finished = true; save(); render(); }));
    if (node.ending) {
      const archivePanel = actions.querySelector(".collection");
      if (archivePanel) for (const action of actions.querySelectorAll(":scope > button")) actions.insertBefore(action, archivePanel);
    }
    save();
  }
  if (!choosing) shell.append(element("p", node.title, "node-title"));
  if (node.text) shell.append(element("p", node.text, "story-note"));
  if (recap?.text) {
    const disclosure = element("details", "", "decision-recap");
    disclosure.append(element("summary", recap.title), element("p", recap.text));
    shell.append(disclosure);
  }
  shell.append(stage, caption, status, actions);
  const entries = journal(story, path);
  if (entries.length && !isV3) {
    const notes = element("details", "", "journal"); notes.append(element("summary", `选择手记 · ${entries.length}`));
    for (const entry of entries) {
      notes.append(element("p", `${entry.title} / ${entry.label}`));
      notes.append(button("从此处分支", () => { path = [...entry.path]; clip = Math.max(0, story.nodes.find(n => n.id === path.at(-1))!.clips.length - 1); time = 0; finished = true; save(); render(); }));
    }
    shell.append(notes);
  }
  root.append(shell);
  showStorageNotice();
  if (finished) showActions();
  else if (current && !pausedByUser) play();
}
window.addEventListener("pagehide", () => { if (video.readyState >= 1) time = video.currentTime; if (root.querySelector(".player")) { rememberAudio(); save(); } });
title();
