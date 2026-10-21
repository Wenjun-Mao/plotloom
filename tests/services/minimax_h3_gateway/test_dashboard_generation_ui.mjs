import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

function harness(post) {
  const fields = new Map();
  const listeners = new Map();
  const events = [];
  const calls = [];
  function el(id) {
    if (!fields.has(id)) fields.set(id, {
      value: "", disabled: true, files: [],
      addEventListener(type, handler) { this[type] = handler; },
      scrollIntoView() {},
    });
    return fields.get(id);
  }
  el("source-mode").value = "url";
  const context = vm.createContext({
    document: { getElementById: el },
    window: {
      addEventListener(type, fn) { listeners.set(type, fn); },
      dispatchEvent(event) { events.push(event); },
    },
    CustomEvent: class { constructor(type, args) { this.type = type; this.detail = args?.detail; } },
    AbortController, setTimeout, clearTimeout, FormData,
    fetch: async (url, args) => {
      if (!args?.method) return { ok: true, json: async () => ({ enabled: true }) };
      calls.push({ url, args });
      return post();
    },
  });
  vm.runInContext(readFileSync("services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/generation.js", "utf8"), context);
  return { el, listeners, calls, events };
}

test("one in-flight submit, accepted ID opens detail, seed remains exact string", async () => {
  let finish;
  const h = harness(() => new Promise((resolve) => { finish = resolve; }));
  await new Promise(setImmediate);
  h.el("generate-seed").value = "9223372036854775807";
  const first = h.el("generation-form").submit({ preventDefault() {} });
  await h.el("generation-form").submit({ preventDefault() {} });
  assert.equal(h.calls.length, 1);
  assert.equal(JSON.parse(h.calls[0].args.body).seed, "9223372036854775807");
  assert.equal(h.el("generation-fields").disabled, true);
  finish({ ok: true, json: async () => ({ id: "h3_" + "a".repeat(32) }) });
  await first;
  assert.equal(h.events[0].type, "dashboard:submitted");
  assert.equal(h.el("generation-fields").disabled, false);
});

test("lost reply warns and refreshes without a second POST or losing draft", async () => {
  const h = harness(() => { throw Error("lost reply"); });
  await new Promise(setImmediate);
  h.el("generate-prompt").value = "keep draft";
  await h.el("generation-form").submit({ preventDefault() {} });
  assert.equal(h.calls.length, 1);
  assert.match(h.el("generation-message").textContent, /可能已创建/);
  assert.equal(h.el("generate-prompt").value, "keep draft");
  assert.equal(h.events[0].type, "dashboard:refresh");
});

test("reuse only fills scalars and clears input media, never submits", () => {
  const h = harness(() => { throw Error("must not submit"); });
  h.el("start-url").value = "https://old.invalid/old.png";
  h.listeners.get("dashboard:reuse")({ detail: { prompt: "new", quality: 8,
    resolution: "704x1280", seed: "9223372036854775807", requestedDurationSeconds: 15,
    aspectPolicy: "contain_pad" } });
  assert.equal(h.el("generate-seed").value, "9223372036854775807");
  assert.equal(h.el("start-url").value, "");
  assert.equal(h.calls.length, 0);
  assert.match(h.el("generation-message").textContent, /尚未提交/);
});
