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
    }
    replaceChildren(...children) {
      this.children = children;
    }
    append(...children) {
      this.children.push(...children);
    }
    addEventListener() {}
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
