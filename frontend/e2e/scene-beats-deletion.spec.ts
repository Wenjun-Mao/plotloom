import { expect, test } from "./fixture";

test.describe("scene-beats structural deletion", () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test("shows an immediately actionable fixed confirmation with exact cascade IDs", async ({ page, workbench }) => {
    const storyboardMutations: string[] = [];
    page.on("request", (request) => {
      const path = new URL(request.url()).pathname;
      if (path.includes("/stages/storyboard") && request.method() !== "GET") storyboardMutations.push(`${request.method()} ${path}`);
    });
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByRole("navigation", { name: "工作台阶段" })
      .getByRole("button", { name: /场景节拍/ }).click();

    // The first scene owns these descendants in the demo.  Cancelling proves
    // the dialog is a review step rather than an eager cascade.
    await page.getByTestId("scene-editor").getByRole("button", { name: "删除场景" }).click();
    const sceneDialog = page.getByTestId("delete-impact");
    await expect(sceneDialog).toBeVisible();
    await expect(sceneDialog).toHaveAttribute("role", "alertdialog");
    await expect(sceneDialog).toContainText("scene_arrival");
    await expect(sceneDialog).toContainText("b1");
    await expect(sceneDialog).toContainText("cue_b1");
    const sceneDownstream = sceneDialog.getByTestId("downstream-storyboard-refs");
    await expect(sceneDownstream).toContainText("shot_scene · shot_01");
    await expect(sceneDownstream).toContainText("storyboard.shots.shot_01.sceneId");
    await expect(sceneDownstream).toContainText("shot_01:b1");
    await expect(sceneDownstream).toContainText("storyboard.shotBeatLinks.shot_01:b1");
    await expect(sceneDownstream).toContainText("storyboard.shots.shot_01.cueIds.cue_b1");
    expect(await sceneDialog.evaluate((element) => getComputedStyle(element).position)).toBe("fixed");
    await sceneDialog.getByRole("button", { name: "取消", exact: true }).click();
    await expect(sceneDialog).toHaveCount(0);
    await expect(page.getByTestId("scene-card-scene_arrival")).toBeVisible();

    // A cue has no same-stage child cascade, yet its scheduled Shot is still
    // disclosed and must be explicitly reviewed before the draft can change.
    const cue = page.getByTestId("cue-card-cue_b1");
    await cue.getByRole("button", { name: "删除 cue" }).click();
    const cueDialog = page.getByTestId("delete-impact");
    const cueDownstream = cueDialog.getByTestId("downstream-storyboard-refs");
    await expect(cueDownstream).toContainText("shot_cue_schedule · shot_01");
    await expect(cueDownstream).toContainText("storyboard.shots.shot_01.cueIds.cue_b1");
    await expect(cueDownstream).not.toContainText("shot_01:b1");
    await cueDialog.getByRole("button", { name: "取消", exact: true }).click();

    // This card is lower in the document.  The same dialog remains above
    // field grids and the sticky topbar, and confirmation removes only the
    // listed beat/cue rather than any sibling scene.
    const beat = page.getByTestId("beat-card-b1");
    await beat.getByRole("button", { name: "删除节拍" }).scrollIntoViewIfNeeded();
    await beat.getByRole("button", { name: "删除节拍" }).click();
    const beatDialog = page.getByTestId("delete-impact");
    await expect(beatDialog).toContainText("b1");
    await expect(beatDialog).toContainText("cue_b1");
    await expect(beatDialog).toContainText("删除场景：无");
    await expect(beatDialog.getByTestId("downstream-storyboard-refs")).toContainText("shot_01:b1");
    await expect(beatDialog.getByTestId("downstream-storyboard-refs")).toContainText("storyboard.shots.shot_01.cueIds.cue_b1");
    expect(await beatDialog.evaluate((element) => getComputedStyle(element).zIndex)).toBe("100");
    await beatDialog.getByTestId("confirm-delete").click();
    await expect(page.getByTestId("beat-card-b1")).toHaveCount(0);
    await expect(page.getByTestId("cue-card-cue_b1")).toHaveCount(0);
    await expect(page.getByTestId("scene-card-scene_arrival")).toBeVisible();

    // A scene confirmation is also a real cascade, not merely a preview: its
    // remaining beat is removed only after this second explicit decision.
    await page.getByTestId("scene-editor").getByRole("button", { name: "删除场景" }).click();
    const finalSceneDialog = page.getByTestId("delete-impact");
    await expect(finalSceneDialog).toContainText("scene_arrival");
    await expect(finalSceneDialog).toContainText("b2");
    await finalSceneDialog.getByTestId("confirm-delete").click();
    await expect(page.getByTestId("scene-card-scene_arrival")).toHaveCount(0);
    await expect(page.getByTestId("beat-card-b2")).toHaveCount(0);
    expect(storyboardMutations).toEqual([]);
  });
});
