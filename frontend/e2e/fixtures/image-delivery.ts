import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { expect } from "@playwright/test";

// Browser fixtures do not launch native tasks; this UUID stands in for their
// manual current_task self-binding without implying a real dispatch.
const CURRENT_TASK_FIXTURE_ID = "00000000-0000-4000-8000-000000000001";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type NativeTaskBinding =
  | { mode: "configured_task"; taskId: string }
  | { mode: "current_task" };

type FrozenImagePackage = {
  packageVersion: number;
  jobId: string;
  requestHash: string;
  executionContract: string;
  nativeTaskBinding: NativeTaskBinding;
  specialistPreflight: {
    version: string;
    executionContract: string;
    skillVersion: string;
  };
  references?: Array<{ role: string; sha256: string }>;
};

type ImageDeliveryOutput = {
  filename: string;
  content: Buffer;
  role: string;
};

type WriteImageDeliveryOptions = {
  packagePath: string;
  deliveryPath: string;
  jobId: string;
  requestHash: string;
  deliveryId: string;
  actualPrompt: string;
  outputs: ImageDeliveryOutput[];
  limitations: string[];
};

export async function writeImageDeliveryFromPackage({
  packagePath,
  deliveryPath,
  jobId,
  requestHash,
  deliveryId,
  actualPrompt,
  outputs,
  limitations,
}: WriteImageDeliveryOptions): Promise<void> {
  const request = JSON.parse(
    await readFile(path.join(packagePath, "request.json"), "utf8"),
  ) as FrozenImagePackage;
  expect(request.packageVersion).toBe(6);
  expect(request.jobId).toBe(jobId);
  expect(request.requestHash).toBe(requestHash);
  expect(request.executionContract).toBe("codex_specialist.v3");
  expect(request.specialistPreflight).toMatchObject({
    version: "p1.5-pin.v2",
    executionContract: "codex_specialist.v3",
    skillVersion: "plotloom-image-specialist.v4",
  });
  expect(outputs.length).toBeGreaterThan(0);

  const nativeTaskId = resolveFixtureNativeTaskId(request.nativeTaskBinding);
  const provenance = {
    codeRevision: "a".repeat(40),
    skillVersion: request.specialistPreflight.skillVersion,
    skillHash: "b".repeat(64),
  };
  const imageGenExecutionId = `exec-${createHash("sha256")
    .update(`${jobId}\0${deliveryId}`)
    .digest("hex")}`;
  expect(imageGenExecutionId).not.toBe(nativeTaskId);

  const outputRoot = path.join(deliveryPath, "outputs");
  await mkdir(outputRoot, { recursive: true });
  for (const output of outputs) {
    await writeFile(path.join(outputRoot, output.filename), output.content);
  }

  const identityReferenceHashes = (request.references ?? [])
    .filter((reference) => reference.role.startsWith("character_identity:") || reference.role === "scene_continuity")
    .map((reference) => reference.sha256);
  const referenceUse = identityReferenceHashes.length > 0
    ? {
        viewedReferenceHashes: [...new Set(identityReferenceHashes)],
        identityNotes: "Fixture attestation only; creator review remains required.",
      }
    : undefined;

  await writeFile(
    path.join(deliveryPath, "executor-pin.json"),
    JSON.stringify({
      jobId,
      requestHash,
      executionContract: request.specialistPreflight.executionContract,
      nativeTaskId,
      ...provenance,
    }),
    "utf8",
  );
  await writeFile(
    path.join(deliveryPath, "completion.json"),
    JSON.stringify({
      schemaVersion: 3,
      jobId,
      requestHash,
      deliveryId,
      actualPrompt,
      outputs: outputs.map((output) => ({
        filename: output.filename,
        sha256: createHash("sha256").update(output.content).digest("hex"),
        role: output.role,
      })),
      toolEvidence: {
        tool: "codex_imagegen",
        nativeTaskId,
        imageGenExecutionId,
        available: true,
      },
      executorProvenance: provenance,
      ...(referenceUse ? { referenceUse } : {}),
      limitations,
    }),
    "utf8",
  );
}

function resolveFixtureNativeTaskId(binding: NativeTaskBinding): string {
  if (binding.mode === "configured_task") {
    if (!UUID_PATTERN.test(binding.taskId)) {
      throw new Error("configured browser fixture binding must contain a native UUID");
    }
    return binding.taskId;
  }
  if (binding.mode === "current_task") return CURRENT_TASK_FIXTURE_ID;
  throw new Error("unsupported native task binding in frozen browser package");
}
