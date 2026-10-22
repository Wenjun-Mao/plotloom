import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";

for (const width of [1280, 1700]) for (const count of [2, 24]) {
  test(`keeps missing-media prose and ${count} exact recovery links readable at ${width}`, async ({ page, request, workbench }) => {
    const project = structuredClone(demoProject);
    project.brief = { ...project.brief, decisionPointsPerPath: 0, endingCount: 1, desiredJoinCount: 0, nodeBudget: 2, maxOutDegree: 1 };
    const original = project.storyboard.shots[0];
    project.storyGraph = { startNodeId: "arrival", nodes: [{ id: "arrival", title: "Missing footage", kind: "start", footageMode: "footage", summary: "Offline layout fixture" }, { id: "ending", title: "End", kind: "ending", footageMode: "footage", summary: "Offline ending" }], edges: [{ id: "finish", sourceNodeId: "arrival", targetNodeId: "ending", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] }], joinContracts: [] };
    const durationUnits = 300;
    project.sceneBeats.scenes = [{ ...project.sceneBeats.scenes[0], beatIds: ["b1"], durationBudgetUnits: durationUnits * (count - 1) }, { ...project.sceneBeats.scenes.find(scene => scene.id === "scene_ending_city")!, storyNodeId: "ending", durationBudgetUnits: durationUnits }];
    project.sceneBeats.beats = project.sceneBeats.beats.filter(beat => ["b1", "b9"].includes(beat.id));
    project.sceneBeats.dialogueCues = [];
    project.storyboard.shots = Array.from({ length: count }, (_, index) => {
      return { ...original, id: `missing-${index}`, sceneId: index === count - 1 ? "scene_ending_city" : original.sceneId, order: index === count - 1 ? 1 : index + 1, durationUnits, audioPlan: { events: [] }, cueIds: [], title: "UnbrokenSourceToken".repeat(5), action: "UnbrokenSourceToken".repeat(3) };
    });
    project.storyboard.shotBeatLinks = project.storyboard.shots.map((shot, index) => ({ shotId: shot.id, beatId: index === count - 1 ? "b9" : "b1", role: index === 0 || index === count - 1 ? "primary" : "supporting", coverageWeight: 1 }));
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: project.brief, initialStages: [
      { stage: "story_bible", payload: project.storyBible }, { stage: "story_graph", payload: project.storyGraph },
      { stage: "scene_beats", payload: project.sceneBeats }, { stage: "storyboard", payload: project.storyboard },
    ] } });
    expect(response.ok(), await response.text()).toBeTruthy();
    const { id } = await response.json();
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&view=play`);
    const warning = page.getByTestId("branching-missing-media");
    await expect(warning).toContainText("待审原片不会自动用于故事。");
    const links = warning.getByRole("link");
    await expect(links).toHaveCount(count);
    await expect(warning.locator("small")).toHaveText(`故事还不能播放：${count} 个镜头缺少当前已确认的播放片段。待审原片不会自动用于故事。`);
    await expect(warning).toContainText("UnbrokenSourceToken".repeat(2));
    expect(new Set(await links.allTextContents()).size).toBe(count);
    const geometry = await warning.evaluate(element => ({ width: element.clientWidth, proseWidth: element.querySelector("small")!.getBoundingClientRect().width, scroll: element.scrollWidth, documentWidth: document.documentElement.scrollWidth }));
    expect(geometry.proseWidth).toBeGreaterThan(geometry.width * 0.8);
    expect(geometry.scroll).toBeLessThanOrEqual(geometry.width);
    expect(geometry.documentWidth).toBeLessThanOrEqual(width);
    const entities = await links.evaluateAll(elements => elements.map(element => new URL((element as HTMLAnchorElement).href).searchParams.get("entity")));
    expect(await links.evaluateAll(elements => elements.map(element => {
      const parameters = new URL((element as HTMLAnchorElement).href).searchParams;
      return { project: parameters.get("project"), stage: parameters.get("stage") };
    }))).toEqual(Array.from({ length: count }, () => ({ project: id, stage: "storyboard" })));
    expect(new Set(entities).size).toBe(count);
    expect([...entities].sort()).toEqual(project.storyboard.shots.map(shot => `shot:${shot.id}`).sort());
    await warning.locator(`a[href*="entity=shot%3Amissing-${count - 1}#"]`).click();
    await expect(page).toHaveURL(new RegExp(`entity=shot%3Amissing-${count - 1}`));
    await expect(page.getByLabel("镜头 ID", { exact: true })).toHaveValue(`missing-${count - 1}`);
  });
}
