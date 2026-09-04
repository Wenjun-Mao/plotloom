import { createHash } from "node:crypto";
import { createServer } from "node:http";

const port = Number(process.argv[process.argv.indexOf("--port") + 1]);
if (!Number.isInteger(port) || port < 1) throw new Error("--port is required");

const state = {
  requests: [],
  sceneTargets: [],
  failedSceneTarget: null,
  failedSceneAttempts: 0,
  holdResponses: false,
  releaseHeldResponses: null,
};

const continuity = () => ({ facts: {}, entityStates: [], screenDirection: null, lighting: null, sound: null, notes: [] });

function jsonAfter(text, marker) {
  const markerIndex = text.lastIndexOf(marker);
  if (markerIndex < 0) return undefined;
  const start = text.slice(markerIndex + marker.length).search(/[\[{]/);
  if (start < 0) return undefined;
  const first = markerIndex + marker.length + start;
  let depth = 0;
  let quoted = false;
  let escaped = false;
  for (let index = first; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === "\"") quoted = false;
      continue;
    }
    if (character === "\"") quoted = true;
    else if (character === "{" || character === "[") depth += 1;
    else if (character === "}" || character === "]") {
      depth -= 1;
      if (depth === 0) return JSON.parse(text.slice(first, index + 1));
    }
  }
  return undefined;
}

function graphFill(topology) {
  return {
    nodes: topology.nodes.map((node, index) => ({ id: node.id, title: `E2E node ${index + 1}`, summary: "The ferry continues through the fog." })),
    edges: topology.edges.map((edge, index) => ({ id: edge.id, choiceText: edge.kind === "choice" ? `Choice ${index + 1}` : null, stateEffects: edge.kind === "choice" ? { route: edge.id } : {} })),
    joinContracts: topology.joinContracts.map((join) => ({ id: join.id, requiredStateKeys: [], allowedDifferences: [], reconciliation: "The routes reunite at the ferry bell.", notes: "" })),
  };
}

function sceneFragment(target) {
  const sceneId = `scene-${target}`;
  const beatId = `beat-${target}`;
  return {
    scenes: [{ localSceneId: sceneId, order: 1, title: "Fog-bound crossing", objective: "Move the story forward", locationId: null, characterIds: [], durationWeight: 1, entryState: continuity(), exitState: continuity() }],
    beats: [{ localBeatId: beatId, sceneLocalId: sceneId, order: 1, description: "The ferry bell sounds once.", purpose: "Advance the story", visibleEvent: "The ferryman grips the bell.", immediateResult: "The crossing continues.", dramaticChange: "The ferry advances.", entryState: continuity(), exitState: continuity(), continuityAnchors: [], continuityDelta: {} }],
    dialogueCues: [],
  };
}

function storyboardFragment(scene, beats) {
  const shotId = `shot-${scene.id}`;
  return {
    shots: [{ localShotId: shotId, order: 1, title: "Ferry bell", shotSize: "medium", durationUnits: 1, cameraAngle: "", cameraMovement: "", composition: "", visualIntent: "Establish the bell", motionIntent: "Stable forward movement", action: "The ferryman grips the bell.", transition: "cut", cueIds: [], audioPlan: { events: [] }, characterIds: [], locationId: null, propIds: [], requiredEntityStates: [], entryState: continuity(), exitState: continuity() }],
    primaryShotLocalIdByBeat: Object.fromEntries(beats.map((beat) => [beat.id, shotId])),
    supportingBeatLinks: [],
  };
}

function storyBible() {
  return { logline: "A ferryman must choose a route through the fog.", premise: "A future letter changes the present crossing.", genre: "mystery", tone: "restrained", audience: "general", narrativePromise: "Every choice alters the crossing.", visualLanguage: "ink wash dawn", themes: [], worldRules: [], knownFacts: [], openQuestions: [], sourceNotes: [], characters: [], locations: [], props: [] };
}

function responsePayload(body) {
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const text = messages.map((message) => String(message?.content ?? "")).join("\n");
  const correction = jsonAfter(text, "【原始工作单元合同】");
  if (text.includes("【纠错轮次】")) {
    // The only planned invalid response is the late scene-beats unit. The
    // correction contract is intentionally metadata-only, so retain its
    // selected target from the primary request rather than infer it from
    // prompt prose that an actual model would never need to parse.
    return correctionSceneResponse(correction?.selectorId);
  }
  const topology = jsonAfter(text, "【不可变图骨架清单】");
  if (topology) return { type: "story_graph", payload: graphFill(topology) };
  const node = jsonAfter(text, "【目标故事节点】");
  if (node) return sceneResponse(node.id, false);
  const scene = jsonAfter(text, "【目标戏剧场景】");
  if (scene) return { type: "storyboard", payload: storyboardFragment(scene, jsonAfter(text, "【该场景节拍】") ?? []) };
  return { type: "story_bible", payload: storyBible() };
}

function sceneResponse(target, correction) {
  if (!correction) state.sceneTargets.push(target);
  if (!state.failedSceneTarget && state.sceneTargets.length === 9) state.failedSceneTarget = target;
  const shouldFail = target === state.failedSceneTarget && state.failedSceneAttempts < 3;
  if (shouldFail) state.failedSceneAttempts += 1;
  return { type: "scene_beats", target, failed: shouldFail, payload: shouldFail ? {} : sceneFragment(target) };
}

function correctionSceneResponse(target) {
  const resolvedTarget = state.failedSceneTarget ?? target;
  const shouldFail = state.failedSceneAttempts < 3;
  if (shouldFail) state.failedSceneAttempts += 1;
  return { type: "scene_beats", target: resolvedTarget, failed: shouldFail, payload: shouldFail ? {} : sceneFragment(resolvedTarget) };
}

function sendJson(response, status, value) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(value));
}

function setResponseHold(enabled) {
  if (enabled) {
    if (!state.holdResponses) {
      state.holdResponses = true;
      state.releaseHeldResponses = null;
    }
    return;
  }
  state.holdResponses = false;
  state.releaseHeldResponses?.();
  state.releaseHeldResponses = null;
}

async function waitForResponseRelease() {
  if (!state.holdResponses) return;
  await new Promise((resolve) => {
    // One release intentionally frees every in-flight fake-provider request.
    // The test fixture is single-process and only uses this as a controllable
    // external network boundary, never as a Plotloom product endpoint.
    state.releaseHeldResponses = resolve;
  });
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  if (request.method === "GET" && url.pathname === "/control/status") {
    return sendJson(response, 200, {
      totalRequests: state.requests.length,
      sceneTargets: state.sceneTargets,
      failedSceneTarget: state.failedSceneTarget,
      failedSceneAttempts: state.failedSceneAttempts,
      requests: state.requests,
      holdResponses: state.holdResponses,
    });
  }
  if (request.method === "POST" && url.pathname === "/control/response-hold") {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    let body;
    try { body = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
    catch { return sendJson(response, 400, { error: "invalid JSON" }); }
    if (typeof body?.enabled !== "boolean") return sendJson(response, 422, { error: "enabled must be boolean" });
    setResponseHold(body.enabled);
    return sendJson(response, 200, { holdResponses: state.holdResponses });
  }
  if (request.method !== "POST" || url.pathname !== "/v1/chat/completions") return sendJson(response, 404, { error: "not found" });
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  let body;
  try { body = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
  catch { return sendJson(response, 400, { error: "invalid JSON" }); }
  const generated = responsePayload(body);
  const content = JSON.stringify(generated.payload);
  state.requests.push({ type: generated.type, target: generated.target ?? null, failed: Boolean(generated.failed), contentHash: createHash("sha256").update(content).digest("hex") });
  await waitForResponseRelease();
  return sendJson(response, 200, {
    id: `fake-${state.requests.length}`,
    model: body.model ?? "external-fake",
    choices: [{ message: { role: "assistant", content }, finish_reason: "stop" }],
    usage: { prompt_tokens: 17, completion_tokens: 23 },
  });
});

server.listen(port, "127.0.0.1");
