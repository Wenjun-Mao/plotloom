import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoProject } from "../src/demo";
import { GraphPage } from "../src/pages/GraphPage";
import { SceneBeatsPage } from "../src/pages/SceneBeatsPage";
import { StoryBiblePage } from "../src/pages/StoryBiblePage";
import { StoryboardPage } from "../src/pages/StoryboardPage";

// The focus contract belongs to the authoring inspectors, not ReactFlow's canvas
// implementation. A small projection keeps this test deterministic in jsdom.
vi.mock("@xyflow/react", () => ({
  Background: () => null,
  BackgroundVariant: { Dots: "dots" },
  Controls: () => null,
  MarkerType: { ArrowClosed: "arrow" },
  MiniMap: () => null,
  ReactFlow: ({ children }: { children?: React.ReactNode }) => createElement("div", { "data-testid": "flow-projection" }, children),
}));

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

async function settle(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => window.setTimeout(resolve, 0));
  });
}

describe("validation issue focus", () => {
  let root: Root;

  beforeEach(() => {
    document.body.innerHTML = '<div id="test-root"></div>';
    root = createRoot(document.getElementById("test-root")!);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
  });

  it("maps an indexed graph node issue to its stable node and title input", async () => {
    const onEntitySelect = vi.fn();
    const node = demoProject.storyGraph.nodes[0];

    await act(async () => root.render(createElement(GraphPage, {
      value: demoProject.storyGraph,
      stale: false,
      saving: false,
      issues: [{ code: "NODE_TITLE", path: "nodes.0.title", message: "标题不能为空" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const field = document.querySelector<HTMLInputElement>(`[data-focus-key="graph:node:${node.id}:title"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`graph-node:${node.id}`);
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("maps a graph state-effect issue to its stable edge row", async () => {
    const onEntitySelect = vi.fn();
    const edgeIndex = demoProject.storyGraph.edges.findIndex((edge) => "memoryBus" in edge.stateEffects);
    const edge = demoProject.storyGraph.edges[edgeIndex];

    await act(async () => root.render(createElement(GraphPage, {
      value: demoProject.storyGraph,
      stale: false,
      saving: false,
      issues: [{ code: "STATE_EFFECT", path: `edges.${edgeIndex}.stateEffects.memoryBus`, message: "状态效果不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const field = document.querySelector<HTMLInputElement>(`[data-focus-key="graph:edge:${edge.id}:stateEffects.memoryBus"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`graph-edge:${edge.id}`);
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("maps an indexed Bible state issue to its stable character and state editor", async () => {
    const onEntitySelect = vi.fn();
    const character = demoProject.storyBible.characters[0];

    await act(async () => root.render(createElement(StoryBiblePage, {
      value: demoProject.storyBible,
      stale: false,
      saving: false,
      issues: [{ code: "STATE_INVALID", path: "characters.0.allowedStates.0", message: "状态不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();

    const issueButton = [...document.querySelectorAll<HTMLButtonElement>("#test-root button")]
      .find((button) => button.textContent?.includes("characters.0.allowedStates.0"));
    expect(issueButton).toBeDefined();
    await act(async () => issueButton!.click());
    await settle();
    await settle();

    const field = document.querySelector<HTMLTextAreaElement>('[data-bible-field="allowedStates"]');
    expect(onEntitySelect).toHaveBeenCalledWith(`bible:character:${character.id}`);
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("focuses the exact nested scene continuity state field", async () => {
    const onEntitySelect = vi.fn();
    const sceneBeats = structuredClone(demoProject.sceneBeats);
    const scene = sceneBeats.scenes[0];
    const character = demoProject.storyBible.characters[0];
    scene.entryState.entityStates = [{ entityType: "character", entityId: character.id, state: character.allowedStates[0] ?? "present" }];

    await act(async () => root.render(createElement(SceneBeatsPage, {
      value: sceneBeats,
      stale: false,
      saving: false,
      issues: [{ code: "CONTINUITY_STATE", path: "scenes.0.entryState.entityStates.0.state", message: "状态不合法" }],
      referenceContext: { characters: demoProject.storyBible.characters },
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const key = `scene-beats:scene:${encodeURIComponent(scene.id)}:entryState.entityStates.0.state`;
    const field = document.querySelector<HTMLInputElement>(`[data-focus-key="${key}"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`scene:${encodeURIComponent(scene.id)}`);
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("focuses the exact scene continuity fact row instead of its fieldset", async () => {
    const onEntitySelect = vi.fn();
    const sceneBeats = structuredClone(demoProject.sceneBeats);
    const scene = sceneBeats.scenes[0];
    scene.entryState.facts = { route: "west" };

    await act(async () => root.render(createElement(SceneBeatsPage, {
      value: sceneBeats,
      stale: false,
      saving: false,
      issues: [{ code: "CONTINUITY_FACT", path: "scenes.0.entryState.facts.route", message: "事实不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const key = `scene-beats:scene:${encodeURIComponent(scene.id)}:entryState.facts.route`;
    const row = document.querySelector<HTMLElement>(`[data-focus-key="${key}"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`scene:${encodeURIComponent(scene.id)}`);
    expect(row?.dataset.recordKey).toBe("route");
    expect(document.activeElement).toBe(row);
  });

  it("focuses the exact beat continuity-delta row for indexed paths", async () => {
    const onEntitySelect = vi.fn();
    const sceneBeats = structuredClone(demoProject.sceneBeats);
    const beat = sceneBeats.beats[0];
    beat.continuityDelta = { route: "west" };

    await act(async () => root.render(createElement(SceneBeatsPage, {
      value: sceneBeats,
      stale: false,
      saving: false,
      issues: [{ code: "CONTINUITY_DELTA", path: "beats.0.continuityDelta.route", message: "delta 不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const key = `scene-beats:beat:${encodeURIComponent(beat.id)}:continuityDelta.route`;
    const row = document.querySelector<HTMLElement>(`[data-focus-key="${key}"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`beat:${encodeURIComponent(beat.id)}`);
    expect(row?.dataset.recordKey).toBe("route");
    expect(document.activeElement).toBe(row);
  });

  it("maps an indexed audio event issue to the stable shot and exact description input", async () => {
    const onEntitySelect = vi.fn();
    const shot = demoProject.storyboard.shots[0];
    const audioEvent = shot.audioPlan.events[0];

    await act(async () => root.render(createElement(StoryboardPage, {
      bible: demoProject.storyBible,
      graph: demoProject.storyGraph,
      sceneBeats: demoProject.sceneBeats,
      value: demoProject.storyboard,
      stale: false,
      mediaTasks: {},
      saving: false,
      issues: [{ code: "AUDIO_DESCRIPTION", path: "shots.0.audioPlan.events.0.description", message: "声音描述不能为空" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const field = document.querySelector<HTMLInputElement>(`[data-focus-key="storyboard:shot:${shot.id}:audioPlan.events.${audioEvent.id}.description"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`shot:${shot.id}`);
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("opens continuity details and focuses an indexed entity-state field", async () => {
    const onEntitySelect = vi.fn();
    const storyboard = structuredClone(demoProject.storyboard);
    const shot = storyboard.shots[0];
    const character = demoProject.storyBible.characters[0];
    shot.entryState.entityStates = [{ entityType: "character", entityId: character.id, state: character.allowedStates[0] ?? "present" }];
    const shotIndex = 0;

    await act(async () => root.render(createElement(StoryboardPage, {
      bible: demoProject.storyBible,
      graph: demoProject.storyGraph,
      sceneBeats: demoProject.sceneBeats,
      value: storyboard,
      stale: false,
      mediaTasks: {},
      saving: false,
      issues: [{ code: "CONTINUITY_STATE", path: `shots.${shotIndex}.entryState.entityStates.0.state`, message: "状态不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const key = `storyboard:shot:${shot.id}:entryState.entityStates.0.state`;
    const field = document.querySelector<HTMLSelectElement>(`[data-focus-key="${key}"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`shot:${shot.id}`);
    expect(field?.closest("details")?.open).toBe(true);
    expect(document.activeElement).toBe(field);
  });

  it("opens details before focusing the exact storyboard continuity fact row", async () => {
    const onEntitySelect = vi.fn();
    const storyboard = structuredClone(demoProject.storyboard);
    const shot = storyboard.shots[0];
    shot.exitState.facts = { route: "east" };

    await act(async () => root.render(createElement(StoryboardPage, {
      bible: demoProject.storyBible,
      graph: demoProject.storyGraph,
      sceneBeats: demoProject.sceneBeats,
      value: storyboard,
      stale: false,
      mediaTasks: {},
      saving: false,
      issues: [{ code: "CONTINUITY_FACT", path: "shots.0.exitState.facts.route", message: "事实不合法" }],
      onEntitySelect,
      onSave: async () => undefined,
    })));
    await settle();
    await settle();

    const key = `storyboard:shot:${shot.id}:exitState.facts.route`;
    const row = document.querySelector<HTMLElement>(`[data-focus-key="${key}"]`);
    expect(onEntitySelect).toHaveBeenCalledWith(`shot:${shot.id}`);
    expect(row?.dataset.recordKey).toBe("route");
    expect(row?.closest("details")?.open).toBe(true);
    expect(document.activeElement).toBe(row);
  });
});
