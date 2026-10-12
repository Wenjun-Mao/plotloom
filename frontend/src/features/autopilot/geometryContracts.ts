/** Server-validated local preparation, distinct from a native image receipt. */
export type GeometryAsset = { assetId: string; originalHash: string; width: number; height: number };
export type GeometryPreparation = {
  version: "geometry-preparation.v1"; preparationId: string; preparationHash: string;
  projectId: string; runId: string; policyHash: string; claim: string; shotId: string;
  source: { asset: GeometryAsset; checkpointId: string; decisionId: string; candidateId: string;
    jobId: string; requestHash: string; deliveryRowId: string; deliveryId: string; manifestHash: string; executionPin: Record<string, string> };
  recipe: { version: "center-cover-rgb-lanczos-png.v1"; exifOrientation: number; orientedWidth: number; orientedHeight: number;
    cropBox: [number, number, number, number]; targetWidth: number; targetHeight: number };
  recipeHash: string; runtime: { pillowVersion: string; transformHash: string }; output: GeometryAsset;
};
