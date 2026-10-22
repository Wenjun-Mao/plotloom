import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

function harness() {
  class Element {
    constructor() {
      this.children = [];
      this.textContent = "";
      this.hidden = false;
      this.classList = { toggle() {} };
      this.events = new Map();
      this.dataset = {};
      this.attributes = new Map();
      this.focusCount = 0;
      this.scrollCount = 0;
    }
    replaceChildren(...children) {
      this.children = children;
    }
    append(...children) {
      this.children.push(...children);
    }
    addEventListener(name, fn) {
      this.events.set(name, fn);
    }
    fire(name) {
      this.events.get(name)?.();
    }
    setAttribute(name, value) {
      this.attributes.set(name, value);
    }
    focus() {
      this.focusCount++;
    }
    scrollIntoView() {
      this.scrollCount++;
    }
  }
  class Video extends Element {}
  const elements = new Map();
  const document = {
    hidden: true,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new Element());
      return elements.get(id);
    },
    createElement(tag) {
      return tag === "video" ? new Video() : new Element();
    },
    addEventListener() {},
  };
  const context = vm.createContext({
    document,
    HTMLVideoElement: Video,
    URL,
    URLSearchParams,
    location: {
      href: "http://localhost/dashboard/?job=h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    window: { history: { pushState() {} }, addEventListener() {} },
    setTimeout() {},
    clearTimeout() {},
    AbortController,
    console,
    fetch() {
      throw Error("must not fetch while hidden");
    },
  });
  vm.runInContext(
    readFileSync(
      "services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/job-list.js",
      "utf8",
    ),
    context,
  );
  vm.runInContext(
    readFileSync(
      "services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/view-state.js",
      "utf8",
    ),
    context,
  );
  vm.runInContext(
    readFileSync(
      "services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/dashboard.js",
      "utf8",
    ),
    context,
  );
  return { context, elements, document };
}

test("selection change immediately withdraws all prior identity-bound fields", () => {
  const { context, document } = harness();
  for (const id of ["detail-id", "frozen", "output-note", "prompt"])
    document.getElementById(id).textContent = "OLD JOB A";
  document.getElementById("detail-fields").children = ["OLD SETTINGS"];
  vm.runInContext('selectJob("h3_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")', context);
  assert.equal(
    document.getElementById("detail-id").textContent,
    "h3_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  );
  assert.equal(document.getElementById("frozen").textContent, "");
  assert.equal(document.getElementById("prompt").textContent, "");
  assert.equal(document.getElementById("detail-fields").children.length, 0);
  assert.equal(document.getElementById("download").hidden, true);
});

test("same-output polling retains the exact existing video element and source", () => {
  const { context, document } = harness();
  const job = {
    id: "h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    backend: "h3_video",
    status: "succeeded",
    quality: 8,
    resolution: "576x1024",
    output: "available",
    expectedDurationSeconds: 124 / 24,
  };
  context.observedJob = job;
  vm.runInContext("renderDetail(observedJob)", context);
  const video = document.getElementById("preview").children[0];
  video.currentTime = 2.5;
  job.generationElapsedMs = 500;
  vm.runInContext("renderDetail(observedJob)", context);
  assert.equal(document.getElementById("preview").children[0], video);
  assert.equal(video.currentTime, 2.5);
  assert.match(video.src, /\/dashboard\/media\/h3_/);
});

test("repeated navigation only commits once after the target response arrives", () => {
  const { context } = harness();
  vm.runInContext(
    `
    pages.accept(pages.request, "second");
    if (!pages.next() || pages.next() || pages.previous()) throw Error("pending transition admitted twice");
    if (pages.current.history.length !== 0) throw Error("page advanced before rows");
    pages.accept(pages.request, "third");
    if (pages.current.cursor !== "second" || pages.current.history.length !== 1) throw Error("wrong accepted page");
    if (!pages.previous() || pages.previous() || pages.next()) throw Error("duplicate back transition");
    pages.accept(pages.request, "second");
    if (pages.current.cursor !== "" || pages.current.history.length) throw Error("back did not restore first page");
  `,
    context,
  );
});

test("failed and superseded transitions preserve committed pagination and query", () => {
  const { context } = harness();
  vm.runInContext(
    `
    pages.accept(pages.request, "second");
    pages.next();
    const failed = pages.request;
    pages.reject(failed);
    if (pages.current.cursor !== "" || pages.current.history.length || !pages.canNext) throw Error("failed page committed");
    pages.reset({search:"new",backend:"h3_video",status:""});
    if (pages.accept(failed,"other") || pages.canNext) throw Error("stale navigation accepted");
    pages.accept(pages.request,null);
    if (pages.current.query.search !== "new" || pages.current.history.length) throw Error("filter did not reset page");
  `,
    context,
  );
});

test("native playback error survives polling without removing a valid download", () => {
  const { context, document } = harness();
  context.job = {
    id: "h3_" + "a".repeat(32),
    backend: "h3_video",
    inputMode: "image",
    output: "available",
  };
  vm.runInContext("renderDetail(job)", context);
  const video = document.getElementById("preview").children[0];
  video.fire("error");
  const warning = document.getElementById("output-note").textContent;
  vm.runInContext("renderDetail(job)", context);
  assert.match(warning, /浏览器无法/);
  assert.equal(document.getElementById("output-note").textContent, warning);
  assert.equal(document.getElementById("preview").children[0], video);
  assert.equal(document.getElementById("download").hidden, false);
  video.fire("loadeddata");
  assert.equal(document.getElementById("output-note").textContent, "可查看");
});

test("new source and expiry clear old failure; removed-source events cannot poison selection", () => {
  const { context, document } = harness();
  context.job = {
    id: "h3_" + "a".repeat(32),
    backend: "h3_video",
    output: "available",
  };
  vm.runInContext("renderDetail(job)", context);
  const removed = document.getElementById("preview").children[0];
  removed.fire("error");
  context.job = { ...context.job, id: "h3_" + "b".repeat(32) };
  vm.runInContext("renderDetail(job)", context);
  removed.fire("error");
  assert.equal(document.getElementById("output-note").textContent, "可查看");
  context.job.output = "expired";
  vm.runInContext("renderDetail(job)", context);
  assert.equal(
    document.getElementById("output-note").textContent,
    "输出已过期",
  );
  assert.equal(document.getElementById("download").hidden, true);
});

test("image load recovery clears its own error without recreating the preview", () => {
  const { context, document } = harness();
  context.job = {
    id: "img_" + "b".repeat(32),
    backend: "qwen_image",
    output: "available",
  };
  vm.runInContext("renderDetail(job)", context);
  const image = document.getElementById("preview").children[0];
  image.fire("error");
  vm.runInContext("renderDetail(job)", context);
  assert.match(
    document.getElementById("output-note").textContent,
    /浏览器无法/,
  );
  image.fire("load");
  assert.equal(document.getElementById("output-note").textContent, "可查看");
  assert.equal(document.getElementById("preview").children[0], image);
});

test("rows expose direct downloads only for available media and details for every job", () => {
  const { context, document } = harness();
  context.jobs = ["available", "expired", "missing", "unavailable", "not_ready"].map(
    (output, index) => ({ id: `h3_${index}`, output }),
  );
  vm.runInContext("renderJobs({jobs})", context);
  const rows = document.getElementById("jobs").children;
  for (let i = 0; i < rows.length; i++) {
    const actions = rows[i].children[4].children[1];
    const [open, download] = actions.children;
    assert.equal(open.textContent, i === 0 ? "预览" : "详情");
    assert.equal(download.hidden, i !== 0);
    assert.match(download.href, new RegExp(`h3_${i}\\?download=true$`));
    assert.match(download.attributes.get("aria-label"), new RegExp(`h3_${i}`));
  }
});

test("explicit selection reveals details once; polling preserves row controls and focus", () => {
  const { context, document } = harness();
  context.jobs = [{ id: "h3_a", output: "available" }];
  vm.runInContext("renderJobs({jobs})", context);
  const row = document.getElementById("jobs").children[0];
  const open = row.children[4].children[1].children[0];
  const title = document.getElementById("detail-title");
  const panel = document.getElementById("detail-panel");
  const before = panel.scrollCount;
  open.onclick();
  assert.equal(panel.scrollCount, before + 1);
  assert.equal(title.focusCount, panel.scrollCount);
  vm.runInContext("renderJobs({jobs}); renderDetail(jobs[0])", context);
  assert.equal(document.getElementById("jobs").children[0], row);
  assert.equal(row.children[4].children[1].children[0], open);
  assert.equal(panel.scrollCount, before + 1);
  document.getElementById("return-to-list").onclick();
  assert.equal(row.children[0].children[0].focusCount, 1);
  context.jobs = [];
  vm.runInContext("renderJobs({jobs})", context);
  document.getElementById("return-to-list").onclick();
  assert.equal(document.getElementById("jobs-title").focusCount, 1);
});

test("row action availability follows polling without retaining an expired download", () => {
  const { context, document } = harness();
  context.jobs = [{ id: "h3_a", output: "available" }];
  vm.runInContext("renderJobs({jobs})", context);
  const row = document.getElementById("jobs").children[0];
  const [open, download] = row.children[4].children[1].children;
  context.jobs[0].output = "expired";
  vm.runInContext("renderJobs({jobs})", context);
  assert.equal(download.hidden, true);
  assert.equal(open.textContent, "详情");
  assert.equal(document.getElementById("jobs").children[0], row);
});
