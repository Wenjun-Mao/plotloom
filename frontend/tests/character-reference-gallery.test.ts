import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { plotloomApi } from "../src/api";
import { CharacterReferenceReviewPanel } from "../src/pages/CharacterReferenceGalleryPage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};

type PendingGallery = {
  project: Deferred<any>;
  cast: Deferred<any>;
  references: Deferred<any>;
  proposals: Deferred<any>;
  workbench: Deferred<any>;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function pendingGallery(): PendingGallery {
  return {
    project: deferred(),
    cast: deferred(),
    references: deferred(),
    proposals: deferred(),
    workbench: deferred(),
  };
}

function galleryResponse(projectId: string, title: string, options: { characters?: { id: string; name: string }[]; decisions?: any[]; proposals?: any[]; assets?: any[] } = {}) {
  const characters = options.characters ?? [{ id: "keeper", name: "Mira" }];
  const asset = { id: "same-asset", projectId, originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-09-20T00:00:00Z", provenance: null };
  const decisions = options.decisions ?? characters.map((character) => ({ id: character.id, projectId, characterId: character.id, referenceRevision: 1, characterContext: {}, characterContextHash: character.id, primaryAssetId: asset.id, complementaryAssetIds: [], assetHashes: [], reviewer: "reviewer", notes: "test", current: true, revokedAt: null, revokedBy: null, revocationReason: null, createdAt: "2026-09-20T00:00:00Z" }));
  return {
    project: { id: projectId, brief: { title } },
    cast: { candidate: null, acceptedCast: { revision: 1, candidateJobId: "cast", contentHash: "cast", binding: {}, acceptedAt: "2026-09-20T00:00:00Z", cast: { characters }, consumerMappings: characters.map((character) => ({ castCharacterId: character.id, consumerCharacterId: character.id })) }, status: "accepted", staleReasons: [] },
    references: { states: [], decisions },
    proposals: { configured: true, proposals: options.proposals ?? [] },
    workbench: { assets: options.assets ?? [asset], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] },
  };
}

function installResolvedGallery(response: ReturnType<typeof galleryResponse>) {
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(response.project as any);
  vi.spyOn(plotloomApi, "getCast").mockResolvedValue(response.cast as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockResolvedValue(response.references as any);
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue(response.proposals as any);
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue(response.workbench as any);
}

function installDeferredGalleries() {
  const galleries = new Map<string, PendingGallery>();
  const signals = new Map<string, AbortSignal[]>();
  const pendingFor = (projectId: string) => {
    let pending = galleries.get(projectId);
    if (!pending) { pending = pendingGallery(); galleries.set(projectId, pending); }
    return pending;
  };
  const recordSignal = (projectId: string, signal?: AbortSignal) => {
    if (!signal) return;
    const projectSignals = signals.get(projectId) ?? [];
    projectSignals.push(signal);
    signals.set(projectId, projectSignals);
  };
  // These promises intentionally ignore AbortSignal: the component's owner guard,
  // rather than cooperative transport cancellation, must reject late completions.
  vi.spyOn(plotloomApi, "getProject").mockImplementation((projectId, signal) => { recordSignal(projectId, signal); return pendingFor(projectId).project.promise; });
  vi.spyOn(plotloomApi, "getCast").mockImplementation((projectId, signal) => { recordSignal(projectId, signal); return pendingFor(projectId).cast.promise; });
  vi.spyOn(plotloomApi, "getCharacterReferences").mockImplementation((projectId, signal) => { recordSignal(projectId, signal); return pendingFor(projectId).references.promise; });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockImplementation((projectId, signal) => { recordSignal(projectId, signal); return pendingFor(projectId).proposals.promise; });
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockImplementation((projectId, signal) => { recordSignal(projectId, signal); return pendingFor(projectId).workbench.promise; });
  return { galleries, signals, pendingFor };
}

async function flushReact() {
  await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 0)); });
}

async function renderProject(projectId: string) {
  window.history.replaceState({}, "", `/?project=${projectId}&stage=characters`);
  await act(async () => { root.render(createElement(CharacterReferenceReviewPanel, { projectId, readOnly: false })); });
  await flushReact();
}

async function resolveGallery(pending: PendingGallery, response: ReturnType<typeof galleryResponse>) {
  await act(async () => {
    pending.project.resolve(response.project);
    pending.cast.resolve(response.cast);
    pending.references.resolve(response.references);
    pending.proposals.resolve(response.proposals);
    pending.workbench.resolve(response.workbench);
    await Promise.resolve();
  });
  await flushReact();
}

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("recovers a failed hero when its preserved component receives another subject identity", async () => {
  installResolvedGallery(galleryResponse("project", "Identity reset fixture", { characters: [{ id: "keeper", name: "Mira" }, { id: "watcher", name: "Nia" }] }));

  await renderProject("project");
  const firstHero = host.querySelector('[data-testid="reference-selected-hero"]')!;
  await act(async () => firstHero.querySelector("img")?.dispatchEvent(new Event("error")));
  expect(firstHero.textContent).toContain("当前已选择的身份参考图像不可用");

  await act(async () => (host.querySelectorAll(".reference-subjects button")[1] as HTMLButtonElement).click());
  await flushReact();
  const secondHero = host.querySelector('[data-testid="reference-selected-hero"]')!;
  expect(secondHero.querySelector("img")).not.toBeNull();
  expect(secondHero.textContent).not.toContain("图像不可用");
});

it("keeps the selected-primary slot when its managed metadata is missing", async () => {
  const candidateAsset = { id: "candidate-asset", projectId: "project", originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-09-20T00:00:00Z", provenance: null };
  const proposal = { id: "proposal", projectId: "project", characterId: "keeper", current: true, parentCandidateAssetId: null, requestHash: "request", request: {}, deliveries: [{ id: "delivery", state: "accepted", candidates: [{ id: "candidate", assetId: candidateAsset.id, asset: candidateAsset, outputHash: "output", role: "original" }] }] };
  const decision = { id: "decision", projectId: "project", characterId: "keeper", referenceRevision: 1, characterContext: {}, characterContextHash: "decision", primaryAssetId: "missing-primary", complementaryAssetIds: [], assetHashes: [], reviewer: "reviewer", notes: "test", current: true, revokedAt: null, revokedBy: null, revocationReason: null, createdAt: "2026-09-20T00:00:00Z" };
  installResolvedGallery(galleryResponse("project", "Missing primary", { decisions: [decision], proposals: [proposal], assets: [candidateAsset] }));

  await renderProject("project");
  const hero = host.querySelector('[data-testid="reference-selected-hero"]')!;
  expect(hero.textContent).toContain("当前已选择的身份参考图像不可用");
  expect(host.querySelector('[data-testid="reference-candidate-hero"]')).toBeNull();
  expect(host.querySelector('[data-testid="reference-candidate-candidate-asset"]')).not.toBeNull();
});

it("does not let an old same-document success replace a settled new project", async () => {
  const { pendingFor, signals } = installDeferredGalleries();

  await renderProject("old-project");
  const old = pendingFor("old-project");
  await renderProject("new-project");
  const fresh = pendingFor("new-project");
  expect(signals.get("old-project")).toHaveLength(5);
  expect(signals.get("old-project")?.every((signal) => signal.aborted)).toBe(true);

  await resolveGallery(fresh, galleryResponse("new-project", "New project"));
  expect(host.textContent).toContain("New project");

  await resolveGallery(old, galleryResponse("old-project", "Old project"));
  expect(host.textContent).toContain("New project");
  expect(host.textContent).not.toContain("Old project");
});

it("does not let an old same-document rejection replace a settled new project", async () => {
  const { pendingFor, signals } = installDeferredGalleries();

  await renderProject("old-project");
  const old = pendingFor("old-project");
  await renderProject("new-project");
  const fresh = pendingFor("new-project");
  expect(signals.get("old-project")?.every((signal) => signal.aborted)).toBe(true);

  await resolveGallery(fresh, galleryResponse("new-project", "New project"));
  expect(host.textContent).toContain("New project");

  await act(async () => {
    old.project.reject(new Error("old request failed"));
    await Promise.resolve();
  });
  await flushReact();
  expect(host.textContent).toContain("New project");
  expect(host.textContent).not.toContain("old request failed");
});
