import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { demoProject } from "../../src/demo";
import { expect } from "../fixture";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
export const retainedStill = path.join(repositoryRoot, "docs/verification/supporting/p0-generated/01-arrival.png");
export const retainedComplementary = path.join(repositoryRoot, "docs/verification/supporting/p15-reference-replacement-stale.png");

type ImageJob = {
  id: string;
  parentCandidateAssetId: string | null;
  requestHash: string;
  request: { kind: "original" | "refinement" };
  deliveries: Array<{ state: string; candidates: Array<{ assetId: string; role: string }> }>;
};
type PackagePaths = { packagePath: string; deliveryPath: string };

export async function createCanonicalProject(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
): Promise<string> {
  const storyboard = structuredClone(demoProject.storyboard);
  const firstShot = storyboard.shots.find((shot) => shot.id === "shot_01")!;
  firstShot.propIds = ["prop_lever"];
  firstShot.requiredEntityStates = [
    { entityType: "prop", entityId: "prop_lever", state: "broken" },
  ];
  const response = await request.post(`${apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `p1-image-brief-${Date.now()}` },
    data: {
      brief: demoProject.brief,
      initialStages: [
        { stage: "story_bible", payload: demoProject.storyBible },
        { stage: "story_graph", payload: demoProject.storyGraph },
        { stage: "scene_beats", payload: demoProject.sceneBeats },
        { stage: "storyboard", payload: storyboard },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { id: string }).id;
}

export async function prepareImageJob(
  page: import("@playwright/test").Page,
  projectId: string,
  testId: string,
): Promise<void> {
  const prepared = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname ===
        `/api/v2/projects/${projectId}/image-jobs`,
  );
  await page.getByTestId(testId).click();
  const response = await prepared;
  expect(response.status(), await response.text()).toBe(201);
}

export async function sendImageJob(
  page: import("@playwright/test").Page,
  projectId: string,
  jobId: string,
): Promise<PackagePaths> {
  const sent = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname ===
        `/api/v2/projects/${projectId}/image-jobs/${jobId}/send`,
  );
  await page.getByTestId(`copy-image-job-${jobId}`).click();
  const response = await sent;
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as PackagePaths;
}

export async function recordSamePersonReview(
  page: import("@playwright/test").Page,
  characterId: string,
): Promise<void> {
  const panel = page.getByTestId("same-person-review-panel");
  await expect(panel).toBeVisible();
  await panel
    .getByLabel("身份对比说明")
    .fill(
      "Human reviewer confirms the stable face, build, and visible character anchors.",
    );
  await panel
    .getByLabel("镜头状态说明")
    .fill(
      "Wardrobe, action, and lighting are reviewed as frozen shot state, not durable identity.",
    );
  await panel
    .getByLabel("复核备注")
    .fill(
      "P1.5 browser regression review; no automated face-recognition claim.",
    );
  await panel
    .getByTestId(`same-person-judgment-${characterId}`)
    .selectOption("pass");
  await panel.getByTestId("record-same-person-review").click();
  await expect(panel.getByText("当前复核", { exact: false })).toBeVisible();
}

export async function latestImageJob(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  projectId: string,
): Promise<ImageJob> {
  const response = await request.get(
    `${apiOrigin}/api/v2/projects/${projectId}/image-jobs`,
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  const payload = (await response.json()) as { jobs: ImageJob[] };
  expect(payload.jobs.length).toBeGreaterThan(0);
  // The public history is newest-first, matching the workbench display.
  return payload.jobs[0]!;
}

export async function imageJob(
  request: import("@playwright/test").APIRequestContext,
  apiOrigin: string,
  projectId: string,
  jobId: string,
): Promise<ImageJob> {
  const response = await request.get(
    `${apiOrigin}/api/v2/projects/${projectId}/image-jobs`,
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  const payload = (await response.json()) as { jobs: ImageJob[] };
  const job = payload.jobs.find((item) => item.id === jobId);
  expect(job).toBeDefined();
  return job!;
}

export async function writeDelivery(
  packagePath: string,
  deliveryPath: string,
  job: ImageJob,
  deliveryId: string,
  role: "original" | "refinement",
): Promise<void> {
  const content = await readFile(retainedStill);
  const outputRoot = path.join(deliveryPath, "outputs");
  const packageRequest = await readJson(
    path.join(packagePath, "request.json"),
  );
  const identityReferenceHashes = packageRequest.references
    .filter((reference: { role: string }) =>
      reference.role.startsWith("character_identity:"),
    )
    .map((reference: { sha256: string }) => reference.sha256);
  const identityAware =
    packageRequest.packageVersion >= 3 && identityReferenceHashes.length > 0;
  await mkdir(outputRoot, { recursive: true });
  await writeFile(path.join(outputRoot, "candidate.png"), content);
  await writeFile(
    path.join(deliveryPath, "completion.json"),
    JSON.stringify({
      schemaVersion: identityAware ? 2 : 1,
      jobId: job.id,
      requestHash: job.requestHash,
      deliveryId,
      actualPrompt:
        "Regression delivery built from the retained P0 image file; no new ImageGen call was made.",
      outputs: [
        {
          filename: "candidate.png",
          sha256: createHash("sha256").update(content).digest("hex"),
          role,
        },
      ],
      toolEvidence: {
        tool: "codex_imagegen",
        taskId: "p1-browser-regression-retained-asset",
        available: true,
      },
      ...(identityAware
        ? {
            referenceUse: {
              viewedReferenceHashes: identityReferenceHashes,
              identityNotes:
                "Fixture attestation only; creator review remains required.",
            },
            executorProvenance: {
              codeRevision: "a".repeat(40),
              skillVersion: "plotloom-image-specialist.v3",
              skillHash: "b".repeat(64),
            },
          }
        : {}),
      limitations: [
        "Retained asset regression only; no new image generation was requested.",
      ],
    }),
    "utf8",
  );
  if (packageRequest.packageVersion >= 4) {
    await writeFile(
      path.join(deliveryPath, "executor-pin.json"),
      JSON.stringify({
        jobId: job.id,
        requestHash: job.requestHash,
        executionContract: "codex_specialist.v2",
        skillVersion: "plotloom-image-specialist.v3",
        codeRevision: "a".repeat(40),
        skillHash: "b".repeat(64),
      }),
      "utf8",
    );
  }
}

export async function readJson(pathname: string): Promise<any> {
  return JSON.parse(await readFile(pathname, "utf8"));
}
