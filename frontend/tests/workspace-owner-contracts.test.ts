import { describe, expect, it } from "vitest";
import { normalizeProfileCatalog } from "../src/app/workspace/useTextProviderProfiles";
import { routeFromLocation, stageForPage } from "../src/app/workspace/contracts";

describe("workspace owner contracts", () => {
  it("normalizes an incomplete profile catalog without treating a missing observation as ready", () => {
    const catalog = normalizeProfileCatalog({
      profiles: [{ profileId: "locked", revision: 3, enabled: false }],
      activeProfileId: "locked",
      selectionRevision: 4,
      presets: {},
    } as never);

    expect(catalog.profiles[0].readiness).toMatchObject({
      profileId: "locked",
      profileRevision: 3,
      state: "disabled",
      reasonCode: "readiness.profile_disabled",
    });
  });

  it("keeps a full URL route, including an entity and run, as one navigation fact", () => {
    window.history.replaceState(null, "", "/?project=project-a&stage=trace&entity=shot-7&run=run-3");

    expect(routeFromLocation()).toEqual({ project: "project-a", stage: "trace", entity: "shot-7", run: "run-3" });
    expect(stageForPage("trace")).toBeUndefined();
    expect(stageForPage("storyboard")).toBe("storyboard");
  });
});
