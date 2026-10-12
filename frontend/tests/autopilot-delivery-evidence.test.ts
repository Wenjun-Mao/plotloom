import { expect, it } from "vitest";
import { deliveryDisclosure } from "../src/features/autopilot/deliveryEvidence";
import { evidenceReadsFixture } from "./autopilot-delivery-fixture";

it("resolves primary, complementary and Art limitations from their exact retained receipts", () => {
  const reads = evidenceReadsFixture();
  for (const id of ["hero-reference", "hero-side", "tower-reference"]) {
    const asset = reads.assets.find(item => item.id === id)!;
    const value = deliveryDisclosure("disposable", { assetId: id, originalHash: asset.originalHash }, reads);
    expect(value.status).toBe("delivered");
    if (value.status === "delivered") {
      expect(value.current.limitations).toEqual(asset.provenance!.limitations);
      expect(value.current.deliveryId).toBe(asset.provenance!.deliveryId);
      expect(value.current.manifestHash).toBe("e".repeat(64));
    }
  }
});

it("keeps original/adapted declarations and geometry separate without judging either", () => {
  const reads = evidenceReadsFixture();
  const value = deliveryDisclosure("disposable", { assetId: "frame-1", originalHash: "1".repeat(64) }, reads);
  expect(value.status).toBe("delivered");
  if (value.status === "delivered") {
    expect(value.current.limitations).toEqual(["适配输出仍需实际检查手部与构图；不代表质量改善。"]);
    expect(value.history[0].evidence!.limitations).toEqual(["原始输出为 941×1672，尺寸与冻结目标不符。"]);
    expect([value.current.asset.width, value.history[0].asset.width]).toEqual([720, 941]);
    expect(value.historyUnknown).toBe(false);
  }
});

it.each(["foreign", "hash", "stale", "missing", "manifest", "receipt", "candidate", "duplicate", "limitations", "candidate-owner", "role", "origin-owner"])("cannot replace unknown evidence with an empty limitations list (%s)", defect => {
  const reads = evidenceReadsFixture();
  const asset = reads.assets.find(item => item.id === "frame-1")!, job = reads.images.find(item => item.id === "adaptation-job")!;
  if (defect === "candidate-owner") job.deliveries[0].candidates[0].jobId = "foreign-job";
  if (defect === "role") job.deliveries[0].candidates[0].role = "original";
  if (defect === "origin-owner") { asset.provenance!.origin = "character_reference_proposal"; job.deliveries[0].candidates[0].asset!.provenance!.origin = "character_reference_proposal"; }
  if (defect === "foreign") job.projectId = "other";
  if (defect === "hash") asset.originalHash = "9".repeat(64);
  if (defect === "stale") job.current = false;
  if (defect === "missing") reads.images = [];
  if (defect === "manifest") job.deliveries[0].manifestHash = null;
  if (defect === "receipt") asset.provenance!.deliveryId = "foreign-delivery";
  if (defect === "candidate") job.deliveries[0].candidates[0].assetId = "other-asset";
  if (defect === "duplicate") reads.images.push(structuredClone(job));
  if (defect === "limitations") delete asset.provenance!.limitations;
  expect(deliveryDisclosure("disposable", { assetId: "frame-1", originalHash: "1".repeat(64) }, reads).status).toBe("unknown");
});

it("distinguishes an explicit empty declaration from missing or unlinked history", () => {
  const reads = evidenceReadsFixture();
  const empty = deliveryDisclosure("disposable", { assetId: "frame-2", originalHash: "2".repeat(64) }, reads);
  expect(empty.status).toBe("delivered");
  if (empty.status === "delivered") expect(empty.current.limitations).toEqual([]);
  reads.images = reads.images.filter(job => job.id !== "original-job");
  const value = deliveryDisclosure("disposable", { assetId: "frame-1", originalHash: "1".repeat(64) }, reads);
  if (value.status !== "delivered") throw new Error("current exact output still exists");
  expect(value.historyUnknown).toBe(true); expect(value.history[0].asset.id).toBe("frame-original"); expect(value.history[0].evidence).toBeUndefined();
});

it.each(["character", "art"])("rejects a foreign %s proposal candidate owner even when its other evidence matches", owner => {
  const reads = evidenceReadsFixture(), proposal = owner === "art" ? reads.art[0] : reads.characters[0];
  const candidate = proposal.deliveries[0].candidates[0]; candidate.proposalId = "foreign";
  const asset = candidate.asset!;
  expect(deliveryDisclosure("disposable", { assetId: asset.id, originalHash: asset.originalHash }, reads).status).toBe("unknown");
});
