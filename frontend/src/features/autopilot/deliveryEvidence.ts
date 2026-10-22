import type { GeometryPreparation } from "./geometryContracts";
import type { ArtReferenceProposal, CharacterReferenceProposal, ImageJob, ManagedAsset } from "../../types";

export type EvidenceReads = { assets: ManagedAsset[]; characters: CharacterReferenceProposal[]; art: ArtReferenceProposal[]; images: ImageJob[] };
export type AssetIdentity = { assetId: string; originalHash: string; geometryPreparation?: GeometryPreparation };
export type DeliveryEvidence = { asset: ManagedAsset; owner: string; candidateId: string; jobId: string; requestHash: string; deliveryId: string; manifestHash: string;
  outputFilename: string; limitations: string[]; source?: AssetIdentity; sourceJobId?: string };
export type Disclosure = { status: "geometry"; asset: ManagedAsset; geometry: GeometryPreparation; source: DeliveryEvidence } | { status: "unknown"; message: string } | { status: "unlinked"; asset: ManagedAsset }
  | { status: "delivered"; current: DeliveryEvidence; history: Array<{ asset: ManagedAsset; evidence?: DeliveryEvidence }>; historyUnknown: boolean };

const generated = new Set(["codex_image_job", "character_reference_proposal", "art_reference_proposal"]);
const sha = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const unknown = (message = "无法核实这张图片对应的原始交付说明。") => ({ status: "unknown" as const, message });

/** Resolve immutable owner receipts, never currentness or visual quality. */
export function deliveryDisclosure(projectId: string, identity: AssetIdentity, reads: EvidenceReads): Disclosure {
  const matches = reads.assets.filter(asset => asset.id === identity.assetId && asset.projectId === projectId && asset.originalHash === identity.originalHash);
  if (!sha(identity.originalHash) || matches.length !== 1) return unknown();
  const asset = matches[0];
  if (!asset.provenance) return unknown("这张图片没有可核实的来源声明。");
  if (asset.provenance.origin !== "plotloom_geometry_preparation" && !generated.has(asset.provenance.origin)) return { status: "unlinked", asset };
  const find = (target: ManagedAsset, requireCurrent = false): DeliveryEvidence | undefined => {
    const evidence: DeliveryEvidence[] = [];
    const owners = [
      ...reads.characters.map(job => ({ owner: "character-reference", origin: "character_reference_proposal", roles: [job.parentCandidateAssetId ? "refinement" : "original"], job, source: undefined, sourceJobId: undefined })),
      ...reads.art.map(job => ({ owner: "art-reference", origin: "art_reference_proposal", roles: ["art_reference"], job, source: undefined, sourceJobId: undefined })),
      ...reads.images.map(job => {
        const adaptation = job.request.frozenSnapshot?.keyframeAdaptation;
        return { owner: "image", origin: "codex_image_job", roles: [job.request.kind], job, source: adaptation && adaptation.sourceOriginalHash ? { assetId: adaptation.sourceAssetId, originalHash: adaptation.sourceOriginalHash } : undefined,
          sourceJobId: adaptation?.sourceJobId };
      }),
    ];
    for (const { owner, origin, roles, job, source, sourceJobId } of owners) {
      if (target.provenance?.origin !== origin || job.projectId !== projectId || !sha(job.requestHash) || requireCurrent && !job.current) continue;
      for (const delivery of job.deliveries) for (const candidate of delivery.candidates) {
        const declaration = candidate.asset?.provenance;
        const candidateOwner = owner === "image" ? ("jobId" in candidate ? candidate.jobId : undefined)
          : ("proposalId" in candidate ? candidate.proposalId : undefined);
        const contradictoryOwner = "jobId" in candidate && candidate.jobId !== job.id
          || "proposalId" in candidate && candidate.proposalId !== job.id;
        if (candidateOwner !== job.id || contradictoryOwner || !new Set<string>(roles).has(candidate.role) || !candidate.asset || !declaration || delivery.state !== "accepted" || !delivery.deliveryId || !sha(delivery.manifestHash)
          || candidate.assetId !== target.id || candidate.outputHash !== target.originalHash
          || candidate.asset?.id !== target.id || candidate.asset.projectId !== projectId || candidate.asset.originalHash !== target.originalHash
          || declaration?.origin !== target.provenance?.origin
          || (declaration.jobId ?? declaration.proposalId) !== job.id || declaration.deliveryId !== delivery.deliveryId
          || declaration.outputFilename !== candidate.outputFilename
          || (target.provenance?.jobId ?? target.provenance?.proposalId) !== job.id || target.provenance?.deliveryId !== delivery.deliveryId
          || target.provenance?.outputFilename !== candidate.outputFilename
          || JSON.stringify(target.provenance?.limitations) !== JSON.stringify(declaration.limitations)
          || !Array.isArray(declaration.limitations) || !declaration.limitations.every(item => typeof item === "string" && item.trim() && item.length <= 2000)) continue;
        evidence.push({ asset: target, owner, candidateId: candidate.id, jobId: job.id, requestHash: job.requestHash, deliveryId: delivery.deliveryId,
          manifestHash: delivery.manifestHash, outputFilename: candidate.outputFilename, limitations: declaration.limitations, source, sourceJobId });
      }
    }
    return evidence.length === 1 ? evidence[0] : undefined;
  };
  if (asset.provenance.origin === "plotloom_geometry_preparation") {
    const geometry = identity.geometryPreparation, sourceAssets = reads.assets.filter(item => geometry
      && item.projectId === projectId && item.id === geometry.source.asset.assetId && item.originalHash === geometry.source.asset.originalHash);
    if (!geometry || geometry.projectId !== projectId || geometry.output.assetId !== asset.id || geometry.output.originalHash !== asset.originalHash
      || geometry.output.width !== asset.width || geometry.output.height !== asset.height || asset.provenance.preparationId !== geometry.preparationId
      || !sha(geometry.preparationHash) || !sha(geometry.recipeHash) || sourceAssets.length !== 1) return unknown("确定性几何处理来源尚待核实。");
    const source = find(sourceAssets[0], true);
    if (!source || source.owner !== "image" || source.candidateId !== geometry.source.candidateId || source.jobId !== geometry.source.jobId
      || source.requestHash !== geometry.source.requestHash || source.deliveryId !== geometry.source.deliveryId || source.manifestHash !== geometry.source.manifestHash) return unknown("几何处理的原始交付说明尚待核实。");
    return { status: "geometry", asset, geometry, source };
  }
  const current = find(asset, true);
  if (!current) return unknown();
  const history: Array<{ asset: ManagedAsset; evidence?: DeliveryEvidence }> = [], visited = new Set([asset.id]);
  let step = current, historyUnknown = false;
  while (step.source) {
    const sources = reads.assets.filter(item => item.id === step.source!.assetId && item.projectId === projectId && item.originalHash === step.source!.originalHash);
    if (!sha(step.source.originalHash) || sources.length !== 1 || visited.has(step.source.assetId)) { historyUnknown = true; break; }
    const source = find(sources[0]);
    if (!source || step.sourceJobId && source.jobId !== step.sourceJobId) { history.push({ asset: sources[0] }); historyUnknown = true; break; }
    history.push({ asset: sources[0], evidence: source }); visited.add(source.asset.id); step = source;
  }
  const job = reads.images.find(item => item.id === current.jobId);
  if (job?.request.kind === "keyframe_adaptation" && !current.source) historyUnknown = true;
  return { status: "delivered", current, history, historyUnknown };
}
