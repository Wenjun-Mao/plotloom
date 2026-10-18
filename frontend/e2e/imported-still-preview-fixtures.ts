import type { APIRequestContext } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect } from "./fixture";
import { json } from "./f5a-fixture";
import { demoProject } from "../src/demo";
import type { ManagedAsset, ReviewedKeyframe, VisualIntent, VisualWorkbench } from "../src/types";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const developmentStillPaths = ["01-arrival.png", "02-keys.png", "03-pressure.png", "04-establishing.png"]
  .map((name) => path.join(repositoryRoot, "docs/verification/supporting/p0-generated", name));

/** Native prerequisites only; each caller owns a fresh project inside its test body. */
export async function createReviewedPreviewProject(request: APIRequestContext, apiOrigin: string, replaceFirstShot = false) {
  const projectId = await createCanonicalProject(request, apiOrigin);
  const base = `${apiOrigin}/api/v2/projects/${projectId}`;
  const read = (): Promise<VisualWorkbench> => json(request.get(`${base}/visual-workbench`));
  const board = await json(request.get(`${base}/storyboard-review`));
  const approval = await json(request.post(`${base}/storyboard-approval`, { data: {
    expectedRevision: board.head.revision, contentHash: board.head.contentHash,
    decision: "approve", reviewer: "P0 native prerequisite fixture", gateSetVersion: board.gateEvaluation.gateSetVersion,
  } }));
  const approvalId: string = approval.decision.id;
  for (const filename of developmentStillPaths) {
    const imported = await json(request.post(`${base}/managed-assets`, { multipart: {
      image: { name: path.basename(filename), mimeType: "image/png", buffer: await readFile(filename) },
      origin: "Direct development-session images generated with imagegen on 2026-09-11",
      rights: "unknown", declared_additions_json: "[]",
    } }));
    expect(imported.provenance.origin).toContain("development-session images");
  }
  const assets = (await read()).assets;
  expect(assets).toHaveLength(4);
  const sourceAsset = assets[0], replacement = assets[1];

  const saveIntent = async (asset: ManagedAsset, shotId: string, sourceBindingId?: string): Promise<VisualIntent> => {
    const intent = {
      role: "shot_keyframe", identityIntent: "Offline fixture identity inspected for this shot.",
      compositionIntent: null, styleIntent: null,
      sourceRefs: [`Explicit P0 native prerequisite for ${shotId}; not creative acceptance.`],
      ...(sourceBindingId ? { sourceBindingId } : {}),
    };
    const entityId = `${shotId}:${asset.id}`;
    const draft = await json(request.put(`${base}/authoring-drafts`, { data: {
      editorScope: "visual_intent", entityId, baseCanonicalRevision: board.head.revision,
      expectedDraftRevision: 0, payload: { assetId: asset.id, shotId, ...intent },
    } }));
    return json(request.post(`${base}/managed-assets/${asset.id}/visual-intents`, { data: {
      ...intent, shotId, consumedDraft: { editorScope: "visual_intent", entityId, draftRevision: draft.draftRevision },
    } }));
  };
  const select = async (asset: ManagedAsset, shotId: string, intent: VisualIntent, compatibilityNote: string): Promise<ReviewedKeyframe> => {
    const state = await read();
    return json(request.post(`${base}/reviewed-keyframes`, { data: {
      assetId: asset.id, shotId, sceneId: "scene_arrival", expectedSelectionRevision: state.selectionRevision,
      storyboardRevision: board.head.revision, approvalId, compatibilityNote,
      visualIntentId: intent.id, visualIntentRevision: intent.revision,
    } }));
  };
  const source = await select(sourceAsset, "shot_01", await saveIntent(sourceAsset, "shot_01"),
    "The retained still matches the approved first-shot composition.");
  await json(request.post(`${base}/character-references`, { data: {
    characterId: "char_ruanxing", authority: "story_bible", primaryAssetId: sourceAsset.id,
    complementaryAssetIds: [], expectedReferenceRevision: 0, reviewer: "Codex",
    notes: "Offline prerequisite reference; not human creative acceptance.",
  } }));
  for (const [shotId, ordinal] of [["shot_02", "second"], ["shot_p0_03", "third"]]) {
    const intent = await saveIntent(sourceAsset, shotId, source.id);
    expect(intent.intent.targetUse).toMatchObject({ targetShotId: shotId, source: { bindingId: source.id } });
    const binding = await select(sourceAsset, shotId, intent,
      `The retained fixture still is explicitly reviewed for the ${ordinal} shot.`);
    const state = await read();
    const review = await json(request.post(`${base}/same-person-reviews`, { data: {
      bindingId: binding.id, expectedReviewRevision: state.samePersonReviews.revision, reviewer: "Codex",
      comparisons: [{ characterId: "char_ruanxing", judgment: "pass",
        identityNotes: "Offline fixture stable identity anchors inspected against the current reference.",
        stateNotes: "Target action, wardrobe and lighting inspected independently." }],
      notes: "Independent target prerequisite review; not human creative acceptance.",
    } }));
    expect(review).toMatchObject({ bindingId: binding.id, current: true, productionEligible: true });
  }
  const preview = async () => {
    const state = await read();
    return json(request.post(`${base}/still-previews`, { data: {
      sceneId: "scene_arrival", shotIds: ["shot_01", "shot_02", "shot_p0_03"],
      expectedSelectionRevision: state.selectionRevision, storyboardRevision: board.head.revision, approvalId,
    } }));
  };
  const prior = await preview();
  if (replaceFirstShot) {
    const replacementIntent = await saveIntent(replacement, "shot_01");
    expect(replacementIntent.revision).toBe(1);
    await select(replacement, "shot_01", replacementIntent,
      "The replacement still matches the approved first-shot composition.");
    expect((await read()).previews.find(item => item.id === prior.id)?.state).toBe("stale");
    await preview();
  }
  const state = await read();
  const current = state.previews.find(item => item.state === "current");
  expect(current?.manifest.frames.map(frame => frame.shotId)).toEqual(["shot_01", "shot_02", "shot_p0_03"]);
  expect(state.samePersonReviews.reviews.filter(item => item.current && item.productionEligible)).toHaveLength(2);
  expect(state.reviewedKeyframes.find(item => item.shotId === "shot_01")?.assetId)
    .toBe(replaceFirstShot ? replacement.id : sourceAsset.id);
  return { projectId, replacementAssetId: replacement.id };
}

export async function createCanonicalProject(request: import("@playwright/test").APIRequestContext, apiOrigin: string): Promise<string> {
  const storyboard = structuredClone(demoProject.storyboard);
  const sceneBeats = structuredClone(demoProject.sceneBeats);
  const first = storyboard.shots.find((shot) => shot.id === "shot_01")!;
  storyboard.shots.push({
    ...first, id: "shot_p0_03", order: 3, title: "P0 静止余波", durationUnits: 2000, cueIds: [],
    audioPlan: { events: first.audioPlan.events.map((event) => ({ ...event, durationUnits: 2000 })) },
  });
  storyboard.shotBeatLinks.push({ shotId: "shot_p0_03", beatId: "b1", role: "supporting", coverageWeight: 1 });
  sceneBeats.scenes = sceneBeats.scenes.map((scene) => scene.id === "scene_arrival"
    ? { ...scene, durationBudgetUnits: 12000 } : scene);
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `p0-still-${Date.now()}` },
    data: {
      brief: demoProject.brief,
      initialStages: [
        { stage: "story_bible", payload: demoProject.storyBible },
        { stage: "story_graph", payload: demoProject.storyGraph },
        { stage: "scene_beats", payload: sceneBeats },
        { stage: "storyboard", payload: storyboard },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json() as { id: string }).id;
}

type RestartEvidence = {
  workbench: Pick<VisualWorkbench, "assets" | "visualIntents" | "reviewedKeyframes" | "characterReferences" | "samePersonReviews">;
  preview: VisualWorkbench["previews"][number];
  originalBytes: Record<string, string>;
};

export async function captureRestartEvidence(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  projectId: string,
): Promise<RestartEvidence> {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const workbench = await response.json() as VisualWorkbench;
  const preview = workbench.previews.find((candidate) => candidate.state === "current");
  expect(preview).toBeDefined();
  const originalBytes = Object.fromEntries(await Promise.all(workbench.assets.map(async (asset) => {
    const original = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/managed-assets/${asset.id}/original`);
    expect(original.ok(), await original.text()).toBeTruthy();
    return [asset.id, (await original.body()).toString("base64")];
  })));
  return {
    workbench: {
      assets: workbench.assets,
      visualIntents: workbench.visualIntents,
      reviewedKeyframes: workbench.reviewedKeyframes,
      characterReferences: workbench.characterReferences,
      samePersonReviews: workbench.samePersonReviews,
    },
    preview: preview!,
    originalBytes,
  };
}
