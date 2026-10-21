"use strict";

// Page rows and their history are one accepted snapshot, never a click counter.
class DashboardPages {
  constructor() {
    this.current = {
      query: { search: "", backend: "", status: "" },
      cursor: "",
      history: [],
      nextCursor: null,
    };
    this.target = null;
    this.ready = false;
  }
  get request() {
    return this.target || this.current;
  }
  get canNext() {
    return this.ready && !this.target && Boolean(this.current.nextCursor);
  }
  get canPrevious() {
    return this.ready && !this.target && this.current.history.length > 0;
  }
  next() {
    if (!this.canNext) return false;
    const page = this.current;
    this.target = {
      query: page.query,
      cursor: page.nextCursor,
      history: [...page.history, page.cursor],
    };
    return true;
  }
  previous() {
    if (!this.canPrevious) return false;
    const page = this.current;
    this.target = {
      query: page.query,
      cursor: page.history.at(-1),
      history: page.history.slice(0, -1),
    };
    return true;
  }
  reset(query) {
    this.target = { query: { ...query }, cursor: "", history: [] };
  }
  accept(request, nextCursor) {
    if (request !== this.request) return false;
    this.current = { ...request, nextCursor };
    this.target = null;
    this.ready = true;
    return true;
  }
  reject(request) {
    if (request === this.target) this.target = null;
  }
}

class DashboardPreview {
  constructor(container, note, labels) {
    this.container = container;
    this.note = note;
    this.labels = labels;
    this.reset();
  }
  reset() {
    this.key = "";
    this.element = null;
    this.failed = false;
    this.container.replaceChildren();
  }
  showNote(output) {
    this.note.textContent = this.failed
      ? "浏览器无法读取或播放此输出；可下载原始文件检查。"
      : this.labels[output] || output;
  }
  render(job) {
    const key = `${job.id}:${job.output}:${job.outputSha256 || ""}`;
    if (key !== this.key) {
      this.reset();
      this.key = key;
      if (job.output === "available") {
        const media = document.createElement(
          job.backend === "h3_video" ? "video" : "img",
        );
        this.element = media;
        media.src = `/dashboard/media/${encodeURIComponent(job.id)}`;
        if (media instanceof HTMLVideoElement) {
          media.controls = true;
          media.preload = "metadata";
          media.playsInline = true;
        } else media.alt = "生成图像原始输出";
        for (const [event, failed] of [
          ["error", true],
          [media instanceof HTMLVideoElement ? "loadeddata" : "load", false],
        ]) {
          media.addEventListener(event, () => {
            if (this.element !== media) return; // Ignore late events from a removed source.
            this.failed = failed;
            this.showNote(job.output);
          });
        }
        this.container.append(media);
      }
    }
    this.showNote(job.output);
  }
}
