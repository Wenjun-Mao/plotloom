import type { ManagedAsset, ImageJob, CharacterReferenceProposal, ArtReferenceProposal } from "../src/types";
import type { EvidenceReads } from "../src/features/autopilot/deliveryEvidence";

/** Declared technical evidence only; no visual judgment or execution. */
export function evidenceReadsFixture(projectId = "disposable"): EvidenceReads {
  const asset = (id: string, hash: string, origin: string, ownerId: string, limitations: string[]): ManagedAsset => ({
    id, projectId, originalHash: hash.repeat(64), displayHash: hash.repeat(64), width: 720, height: 1280,
    mimeType: "image/png", byteSize: 64, createdAt: "2026-10-12",
    provenance: { origin, rights: "unknown", rightsNote: null, declaredAdditions: [],
      ...(origin === "codex_image_job" ? { jobId: ownerId } : { proposalId: ownerId }),
      deliveryId: `delivery-${id}`, outputFilename: `${id}.png`, limitations },
  });
  const primary = asset("hero-reference", "a", "character_reference_proposal", "hero-job", ["主参考：服装细节仍须人工核查。"]);
  const side = asset("hero-side", "b", "character_reference_proposal", "hero-side-job", ["补充参考：侧脸仍须人工核查。"]);
  const art = asset("tower-reference", "c", "art_reference_proposal", "tower-job", ["额外椅子、花瓶与植物偏离冻结要求。"]);
  const original = asset("frame-original", "d", "codex_image_job", "original-job", ["原始输出为 941×1672，尺寸与冻结目标不符。"]);
  original.width = 941; original.height = 1672;
  const adapted = asset("frame-1", "1", "codex_image_job", "adaptation-job", ["适配输出仍需实际检查手部与构图；不代表质量改善。"]);
  const empty = asset("frame-2", "2", "codex_image_job", "empty-job", []);
  const delivery = <Role extends "original" | "keyframe_adaptation" | "art_reference">(value: ManagedAsset, ownerId: string, role: Role) => ({
    id: `receipt-${value.id}`, deliveryId: `delivery-${value.id}`, state: "accepted" as const, diagnosticCode: null,
    manifestHash: "e".repeat(64), createdAt: "2026-10-12", publicationPhase: "final" as const,
    candidates: [{ id: `candidate-${value.id}`, assetId: value.id, jobId: ownerId, proposalId: ownerId,
      outputFilename: `${value.id}.png`, outputHash: value.originalHash, role, asset: value, createdAt: "2026-10-12" }],
  });
  const proposal = (value: ManagedAsset, id: string) => ({ id, projectId, characterId: "hero", subjectType: "scene" as const,
    subjectId: "tower", parentCandidateAssetId: null, request: {}, requestHash: "f".repeat(64), state: "delivered" as const,
    current: true, exportedAt: null, cancelledAt: null, cancellationReason: null, createdAt: "2026-10-12", deliveries: [delivery(value, id, "original")] });
  const image = (value: ManagedAsset, id: string): ImageJob => ({ id, projectId, productionUnitId: "fixture-unit", parentJobId: null, parentCandidateAssetId: null,
    request: { kind: "original" }, requestHash: "f".repeat(64), state: "delivered", current: true,
    exportedAt: null, cancelledAt: null, cancellationReason: null, createdAt: "2026-10-12", deliveries: [delivery(value, id, "original")] });
  const adaptation = image(adapted, "adaptation-job");
  adaptation.request = { kind: "keyframe_adaptation", frozenSnapshot: { keyframeAdaptation: {
    sourceJobId: "original-job", sourceAssetId: original.id, sourceOriginalHash: original.originalHash,
    targetProfile: { id: "fixture-geometry", width: 720, height: 1280 },
  } } };
  adaptation.deliveries = [delivery(adapted, "adaptation-job", "keyframe_adaptation")];
  const artProposal = { ...proposal(art, "tower-job"), deliveries: [delivery(art, "tower-job", "art_reference")] };
  return { assets: [primary, side, art, original, adapted, empty],
    characters: [proposal(primary, "hero-job"), proposal(side, "hero-side-job")] as CharacterReferenceProposal[],
    art: [artProposal] as ArtReferenceProposal[], images: [image(original, "original-job"), adaptation, image(empty, "empty-job")] };
}
