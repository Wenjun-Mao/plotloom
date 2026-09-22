import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ArtPanel } from "../src/pages/ArtPanel";
import type { ArtBinding, ArtReferenceProposal, ArtReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

const study: ArtReferenceProposal = {
  id: "study-1", projectId: "old", subjectType: "scene", subjectId: "S01", request: {}, requestHash: "request",
  state: "prepared", current: true, exportedAt: null, cancelledAt: null, cancellationReason: null, createdAt: "2026-09-18T00:00:00Z", deliveries: [],
};

const deliveredStudy: ArtReferenceProposal = {
  ...study, state: "delivered", deliveries: [{
    id: "delivery-1", deliveryId: "delivery-1", state: "accepted", diagnosticCode: null, manifestHash: "manifest",
    createdAt: "2026-09-18T00:00:00Z", candidates: [{
      id: "candidate-1", assetId: "asset-1", proposalId: study.id, outputFilename: "scene.png", outputHash: "a".repeat(64), role: "art_reference",
      createdAt: "2026-09-18T00:00:00Z", asset: {
        id: "asset-1", projectId: "old", originalHash: "a".repeat(64), displayHash: "b".repeat(64), mimeType: "image/png",
        byteSize: 1, width: 1, height: 1, createdAt: "2026-09-18T00:00:00Z", provenance: { origin: "test", rights: "unknown", rightsNote: null, declaredAdditions: [] },
      },
    }],
  }],
};

function artState(projectId: string): ArtReviewState {
  return {
    candidate: null,
    acceptedArt: {
      revision: 1, candidateJobId: "art-1", contentHash: "accepted", acceptedAt: "2026-09-18T00:00:00Z",
      binding: {} as ArtBinding,
      art: { scenes: [{ id: "S01", name: "Held scene" }], props: [] },
    },
    status: "accepted", staleReasons: [],
  };
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("settles a deferred F3B copy after unmount without refresh, assignment, or error publication", async () => {
  const copied = deferred<{ proposal: ArtReferenceProposal; assignment: string; packagePath: string; deliveryPath: string }>();
  const getArt = vi.spyOn(plotloomApi, "getArt").mockImplementation(async (projectId) => artState(projectId));
  const getStudies = vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [study] });
  const getDecisions = vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  vi.spyOn(plotloomApi, "copyArtReferenceProposal").mockReturnValue(copied.promise);

  await act(async () => { root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })); });
  const copy = [...host.querySelectorAll("button")].find((button) => button.textContent === "复制 ImageGen 任务");
  expect(copy).toBeDefined();
  await act(async () => copy?.click());
  const artCallsBeforeUnmount = getArt.mock.calls.length;
  const studyCallsBeforeUnmount = getStudies.mock.calls.length;
  const decisionCallsBeforeUnmount = getDecisions.mock.calls.length;
  await act(async () => root.unmount());

  await act(async () => {
    copied.resolve({ proposal: study, assignment: "stale assignment", packagePath: "package", deliveryPath: "delivery" });
    await copied.promise;
  });

  expect(getArt).toHaveBeenCalledTimes(artCallsBeforeUnmount);
  expect(getStudies).toHaveBeenCalledTimes(studyCallsBeforeUnmount);
  expect(getDecisions).toHaveBeenCalledTimes(decisionCallsBeforeUnmount);
  expect(host.textContent).not.toContain("stale assignment");
  expect(host.querySelector('[role="alert"]')).toBeNull();
});

it("settles a deferred explicit F3B reference choice after unmount without a stale refresh", async () => {
  const chosen = deferred<{ id: string }>();
  const getArt = vi.spyOn(plotloomApi, "getArt").mockImplementation(async (projectId) => artState(projectId));
  const getStudies = vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [deliveredStudy] });
  const getDecisions = vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({
    states: [{ subjectType: "scene", subjectId: "S01", revision: 0, activeDecisionId: null, current: false }], decisions: [],
  });
  const createDecision = vi.spyOn(plotloomApi, "createArtReferenceDecision").mockReturnValue(chosen.promise as Promise<any>);

  await act(async () => { root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })); });
  const choose = [...host.querySelectorAll("button")].find((button) => button.textContent === "用作此环境的参考图");
  expect(choose).toBeDefined();
  await act(async () => choose?.click());
  expect(createDecision).toHaveBeenCalledWith("old", {
    subjectType: "scene", subjectId: "S01", assetId: "asset-1", expectedReferenceRevision: 0,
  });
  const before = [getArt.mock.calls.length, getStudies.mock.calls.length, getDecisions.mock.calls.length];
  await act(async () => root.unmount());
  await act(async () => { chosen.resolve({ id: "decision-1" }); await chosen.promise; });

  expect([getArt.mock.calls.length, getStudies.mock.calls.length, getDecisions.mock.calls.length]).toEqual(before);
  expect(host.querySelector('[role="alert"]')).toBeNull();
});
