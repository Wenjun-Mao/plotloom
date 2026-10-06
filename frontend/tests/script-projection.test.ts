import { expect, it } from "vitest";
import type { ScriptBinding } from "../src/types";
import { sectionEpisode } from "../src/features/graph/scriptProjection";

const binding = { sectionBindings: [{ sectionId: "opening", episode: 7 }], routeOnlySectionIds: ["choice"] } as ScriptBinding;
const scene = { sceneId: "S01", lighting: "dawn", characters: ["keeper"], props: [], flow: [{ speaker: "keeper", line: "Choose.", delivery: "quiet" }] };

it("retains the raw episode and every repeated scene occurrence through exact binding", () => {
  const episode = { ep: 7, targetSeconds: 90, hook: "entry", cliff: "terminal", hookBeat: [1, 1], beatsClaimed: [], scenes: [scene, structuredClone(scene)] };
  const script = { episodes: [{ ...episode, ep: 1 }, episode] };
  expect(sectionEpisode(script, binding, "opening")).toBe(episode);
  expect(sectionEpisode(script, binding, "opening")?.scenes).toHaveLength(2);
  expect(sectionEpisode(script, binding, "choice")).toBeNull();
});

it("rejects missing or ambiguous current bindings instead of inferring episode order", () => {
  const episode = { ep: 7, scenes: [scene] };
  expect(() => sectionEpisode({ episodes: [episode] }, binding, "unknown")).toThrow("尚未绑定");
  expect(() => sectionEpisode({ episodes: [{ ...episode, ep: 1 }] }, binding, "opening")).toThrow("不唯一或缺失");
  expect(() => sectionEpisode({ episodes: [episode, episode] }, binding, "opening")).toThrow("不唯一或缺失");
});
