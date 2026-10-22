import { expect, it } from "vitest";
import { shotLabel, storyShotLabel } from "../src/shot-label";
import { demoProject } from "../src/demo";
import { shotImageJobs } from "../src/features/media/image-jobs/image-job-visibility";
import type { ImageJob } from "../src/types";

it("keeps short labels and derives bounded labels from action without mutating production source", () => {
  expect(shotLabel({ id: "shot", title: "窗外停步" })).toBe("窗外停步");
  const shot = { id: "ending-a-s1-c3", title: "Long generation direction. ".repeat(20), action: "林遥在窗外停下，神情安静。" };
  const original = JSON.stringify(shot);
  expect(shotLabel(shot)).toBe(shot.action);
  expect(JSON.stringify(shot)).toBe(original);
  expect(shotLabel({ ...shot, action: undefined })).toBe(shot.id);
  expect(Array.from(shotLabel({ ...shot, action: "🙂".repeat(70) })).length).toBe(52);
});

it("defaults image-job history to the exact shot and retains full project history separately", () => {
  const jobs = [
    { id: "current", request: { frozenSnapshot: { shot: { id: "b2" } } } },
    { id: "other", request: { frozenSnapshot: { shot: { id: "b1" } } } },
    { id: "unknown", request: {} },
  ] as ImageJob[];
  expect(shotImageJobs(jobs, "b2").map(job => job.id)).toEqual(["current"]);
  expect(shotImageJobs(jobs)).toBe(jobs);
});

it("distinguishes story positions with identical shot prose without changing source", () => {
  const project = structuredClone(demoProject);
  for (const shot of project.storyboard.shots) { shot.title = ""; shot.action = "相同的镜头动作"; }
  for (const node of project.storyGraph.nodes) node.title = "同名剧情节点";
  const original = JSON.stringify(project);
  const labels = project.storyboard.shots.map(shot => storyShotLabel(shot.id, project.storyboard, project.sceneBeats, project.storyGraph));
  expect(new Set(labels).size).toBe(labels.length);
  expect(labels.every(label => label.startsWith("节点 "))).toBe(true);
  expect(labels.every(label => label.includes("场次 ") && label.includes("镜头 ") && label.endsWith("相同的镜头动作"))).toBe(true);
  expect(storyShotLabel("unknown-shot", project.storyboard, project.sceneBeats, project.storyGraph)).toBe("unknown-shot");
  expect(JSON.stringify(project)).toBe(original);
});

it("keeps node positions distinct when authored titles imitate their qualifiers", () => {
  const project = structuredClone(demoProject);
  const nodeTitles = ["Ending", "Ending", "节点 1：Ending"];
  const shots = project.storyGraph.nodes.slice(0, 3).map((node, index) => {
    node.title = nodeTitles[index];
    const scene = project.sceneBeats.scenes.find(item => item.storyNodeId === node.id)!;
    const shot = project.storyboard.shots.filter(item => item.sceneId === scene.id).sort((a, b) => a.order - b.order)[0];
    shot.title = "";
    shot.action = "相同的镜头动作";
    return shot;
  });
  const original = JSON.stringify(project);
  const labels = shots.map(shot => storyShotLabel(shot.id, project.storyboard, project.sceneBeats, project.storyGraph));
  expect(labels).toEqual([
    "节点 1：Ending · 场次 1 · 镜头 1：相同的镜头动作",
    "节点 2：Ending · 场次 1 · 镜头 1：相同的镜头动作",
    "节点 3：节点 1：Ending · 场次 1 · 镜头 1：相同的镜头动作",
  ]);
  expect(new Set(labels).size).toBe(shots.length);
  expect(JSON.stringify(project)).toBe(original);
});
