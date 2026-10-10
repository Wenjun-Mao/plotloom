import { act, createElement } from "react";

import type { Root } from "react-dom/client";

import App from "../src/App";

import { demoProject } from "../src/demo";

import type { MediaTask, ProjectCreationResponse, ProjectListItem, ServerStageName, StageEnvelope } from "../src/types";

export function resource(id: string, title: string, revision = 1): ProjectListItem {
  return {
    id,
    revision,
    brief: { ...demoProject.brief, title },
    lifecycleRevision: 1,
    lifecycleStatus: "active",
    archivedAt: null,
    createdAt: "2026-08-30T00:00:00Z",
    updatedAt: "2026-08-30T00:00:00Z",
    stageStatuses: { story_bible: "missing", story_graph: "missing", scene_beats: "missing", storyboard: "missing" },
    latestRun: null,
  };
}

export function mediaTask(overrides: Partial<MediaTask>): MediaTask {
  return {
    id: "task",
    projectId: "media-project",
    shotId: "shot_01",
    storyboardRevision: 1,
    kind: "image",
    status: "queued",
    derivedPrompt: "prompt",
    promptComponents: {},
    provider: "fixture",
    publicSettings: {},
    providerTaskId: null,
    outputUri: null,
    error: null,
    createdAt: "2026-08-30T00:00:00Z",
    updatedAt: "2026-08-30T00:00:00Z",
    startedAt: null,
    finishedAt: null,
    ...overrides,
  };
}

export function stageEnvelopes(payloads: Partial<Record<ServerStageName, unknown>> = {}): StageEnvelope[] {
  return (["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => ({
    head: {
      stage,
      revision: payloads[stage] == null ? 0 : 1,
      status: payloads[stage] == null ? "missing" : "ready",
      entityRevisionId: payloads[stage] == null ? null : `${stage}-r1`,
      contentHash: payloads[stage] == null ? null : `${stage}-hash`,
      schemaVersion: 2,
      inputRevisions: {},
      staleReasons: [],
      updatedAt: "2026-08-30T00:00:00Z",
    },
    payload: payloads[stage] ?? null,
  }));
}

export function creationResponse(
  id: string,
  title: string,
  payloads: Partial<Record<ServerStageName, unknown>> = {},
  revision = 1,
): ProjectCreationResponse {
  return { ...resource(id, title, revision), stages: stageEnvelopes(payloads) };
}

export function button(label: string): HTMLButtonElement {
  const found = [...document.querySelectorAll("button")].find((candidate) => candidate.textContent?.includes(label));
  if (!found) throw new Error(`Button not found: ${label}`);
  return found as HTMLButtonElement;
}

export function setInput(input: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

export async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => window.setTimeout(resolve, 0));
  });
}

export async function renderSample(root: Root): Promise<void> {
  await act(async () => root.render(createElement(App)));
  await flush();
  await act(async () => button("打开示例项目").click());
  await flush();
}

export async function renderBlank(root: Root): Promise<void> {
  await act(async () => root.render(createElement(App)));
  await flush();
  await act(async () => button("创建空白项目").click());
  await flush();
}

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}
