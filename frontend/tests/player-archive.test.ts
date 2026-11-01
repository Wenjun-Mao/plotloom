import { expect, it } from "vitest";
import { readArchive, recordRoute, journal } from "../src/player/archive";
import type { Story } from "../src/player/state";
const story: Story = { format: 1, gameId: "v2", storyRevision: "r", assetVersion: "a", title: "", intro: "", start: "c", nodes: [
  { id: "c", title: "Decision", clips: [], question: "Choose", edges: [{ id: "a", to: "a", label: "Keep" }, { id: "b", to: "b", label: "Leave" }], ending: null },
  ...["a", "b"].map(id => ({ id, title: id, clips: [], question: "", edges: [], ending: { title: id, text: "" } })),
] };
it("retains both completed routes when forking and does not invent endings from malformed storage", () => {
  let archive = readArchive(story, null);
  archive = recordRoute(archive, ["c", "a"]);
  archive = recordRoute(archive, ["c", "b"]);
  archive = recordRoute(archive, ["c", "a"]);
  expect(readArchive({ ...story, assetVersion: "replacement" }, archive).routes).toHaveLength(2);
  expect(journal(story, ["c", "b"])).toEqual([{ title: "Choose", label: "Leave", path: ["c"] }]);
  expect(readArchive(story, { revision: "r", routes: [{ path: ["c", "missing"], ending: "missing" }, { path: ["c"], ending: "a" }] }).routes).toEqual([]);
  expect(readArchive({ ...story, storyRevision: "new-story" }, archive).routes).toEqual([]);
});
