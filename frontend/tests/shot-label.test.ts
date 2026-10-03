import { expect, it } from "vitest";
import { shotLabel } from "../src/shot-label";
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
