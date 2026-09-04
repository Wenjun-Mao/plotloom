import { beforeEach, describe, expect, it } from "vitest";
import { discardDraft, draftKey, findRevisionConflict, getDraft, putDraft } from "../src/draft-registry";
import { demoProject } from "../src/demo";

describe("draft registry", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("isolates drafts by project/new, stage, and their base revision", () => {
    const project = { ...demoProject, id: "project-a", revision: 4, stageRevisions: { ...demoProject.stageRevisions, story_bible: 9 } };
    const brief = putDraft(project, "brief", { title: "brief draft" });
    const bible = putDraft(project, "story_bible", { logline: "bible draft" });

    expect(brief.key).toBe("project-a:brief:4");
    expect(bible.key).toBe("project-a:story_bible:9");
    expect(getDraft(project, "brief")?.payload).toEqual({ title: "brief draft" });
    expect(draftKey({ ...project, revision: 5 }, "brief")).toBe("project-a:brief:5");
    discardDraft(project, "brief");
    expect(getDraft(project, "brief")).toBeUndefined();
    expect(getDraft(project, "story_bible")?.payload).toEqual({ logline: "bible draft" });
  });

  it("uses an explicit owner for each unsaved workspace", () => {
    const blank = { ...demoProject, id: undefined, clientDraftOwner: "blank", revision: 0 };
    const sample = { ...demoProject, id: undefined, clientDraftOwner: "sample", revision: 0 };
    expect(draftKey(blank, "brief")).toBe("local:blank:brief:0");
    expect(draftKey(sample, "brief")).toBe("local:sample:brief:0");
    putDraft(blank, "brief", { title: "blank only" });
    expect(getDraft(sample, "brief")).toBeUndefined();
  });

  it("finds a same-project stale revision without making it recoverable", () => {
    const project = { ...demoProject, id: "project-a", revision: 4 };
    putDraft(project, "brief", { title: "old draft" });
    const newer = { ...project, revision: 5 };

    expect(getDraft(newer, "brief")).toBeUndefined();
    expect(findRevisionConflict(newer, "brief")).toMatchObject({ key: "project-a:brief:4", payload: { title: "old draft" } });
  });
});
