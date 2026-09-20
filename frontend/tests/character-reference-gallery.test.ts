import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { plotloomApi } from "../src/api";
import { CharactersPage } from "../src/pages/CharactersPage";

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

function galleryResponse(projectId: string, title: string, options: { characters?: { id: string; name: string }[]; decisions?: any[]; referenceStates?: any[]; proposals?: any[]; assets?: any[] } = {}) {
  const characters = options.characters ?? [{ id: "keeper", name: "Mira" }];
  const asset = { id: "same-asset", projectId, originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-09-20T00:00:00Z", provenance: null };
  const decisions = options.decisions ?? characters.map((character) => ({ id: character.id, projectId, characterId: character.id, referenceRevision: 1, characterContext: {}, characterContextHash: character.id, primaryAssetId: asset.id, complementaryAssetIds: [], assetHashes: [], reviewer: "reviewer", notes: "test", current: true, revokedAt: null, revokedBy: null, revocationReason: null, createdAt: "2026-09-20T00:00:00Z" }));
  return {
    project: { id: projectId, brief: { title } },
    cast: { candidate: null, acceptedCast: { revision: 1, candidateJobId: "cast", contentHash: "cast", binding: {}, acceptedAt: "2026-09-20T00:00:00Z", cast: { characters }, consumerMappings: characters.map((character) => ({ castCharacterId: character.id, consumerCharacterId: character.id })) }, status: "accepted", staleReasons: [] },
    references: { states: options.referenceStates ?? [], decisions },
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
  await act(async () => { root.render(createElement(CharactersPage, { projectId, readOnly: false })); });
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

function changeValue(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value");
  descriptor?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

function button(label: string): HTMLButtonElement {
  const found = [...host.querySelectorAll("button")].find((entry) => entry.textContent === label);
  if (!found) throw new Error(`Missing button: ${label}`);
  return found as HTMLButtonElement;
}

function candidateProposal(projectId: string, characterId = "keeper") {
  const asset = { id: `${characterId}-asset`, projectId, originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-09-20T00:00:00Z", provenance: null };
  return { asset, proposal: { id: `${characterId}-proposal`, projectId, characterId, current: true, parentCandidateAssetId: null, requestHash: "request", request: {}, deliveries: [{ id: `${characterId}-delivery`, state: "accepted", candidates: [{ id: `${characterId}-candidate`, assetId: asset.id, asset, outputHash: "output", role: "original" }] }] } };
}

function castAtRevision(response: ReturnType<typeof galleryResponse>, status: "accepted" | "reopened", revision: number) {
  return {
    ...response.cast,
    status,
    acceptedCast: { ...response.cast.acceptedCast, revision, contentHash: `cast-${revision}` },
  };
}

it("does not refresh an old image mutation after reopening invalidates its cast session", async () => {
  const { asset, proposal } = candidateProposal("project");
  const response = galleryResponse("project", "Session fixture", { decisions: [], referenceStates: [{ characterId: "keeper", revision: 3 }], proposals: [proposal], assets: [asset] });
  installResolvedGallery(response);
  const selection = deferred<any>();
  vi.spyOn(plotloomApi, "selectCharacterReference").mockImplementation(() => selection.promise);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue({ ...response.cast, status: "reopened" } as any);

  await renderProject("project");
  const notes = host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement;
  await act(async () => { changeValue(notes, "Explicit reviewer note"); });
  await act(async () => { button("选择身份参考").click(); await Promise.resolve(); });
  expect(button("重新打开角色提案").disabled).toBe(false);
  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已接受角色已过期");
  const galleryReadsBeforeOldSuccess = vi.mocked(plotloomApi.getCharacterReferenceProposals).mock.calls.length;

  await act(async () => { selection.resolve({}); await Promise.resolve(); });
  await flushReact();
  expect(vi.mocked(plotloomApi.getCharacterReferenceProposals).mock.calls).toHaveLength(galleryReadsBeforeOldSuccess);
  expect(host.textContent).not.toContain("角色参考操作失败");
});

it("does not retain a copied assignment from a cast session invalidated in flight", async () => {
  const { asset, proposal } = candidateProposal("project");
  const response = galleryResponse("project", "Assignment fixture", { decisions: [], referenceStates: [{ characterId: "keeper", revision: 3 }], proposals: [proposal], assets: [asset] });
  installResolvedGallery(response);
  const copied = deferred<any>();
  const reopening = deferred<any>();
  vi.spyOn(plotloomApi, "copyCharacterReferenceProposal").mockImplementation(() => copied.promise);
  vi.spyOn(plotloomApi, "reopenCast").mockImplementation(() => reopening.promise);

  await renderProject("project");
  await act(async () => { button("复制 handoff").click(); await Promise.resolve(); });
  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("角色文字正在更新");
  expect(button("复制 handoff").disabled).toBe(true);
  await act(async () => { copied.resolve({ assignment: "old-session assignment must not appear" }); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).not.toContain("old-session assignment must not appear");
  await act(async () => { reopening.resolve({ ...response.cast, status: "reopened" }); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已接受角色已过期");
});

it("replaces a held initial gallery read after reopen and save settle a newer same-subject cast session", async () => {
  const initial = galleryResponse("project", "Old initial gallery evidence");
  const current = galleryResponse("project", "Current live gallery evidence");
  current.references.decisions[0].referenceRevision = 2;
  const held = pendingGallery();
  let projectReads = 0; let referenceReads = 0; let proposalReads = 0; let workbenchReads = 0;
  vi.spyOn(plotloomApi, "getCast").mockResolvedValue(initial.cast as any);
  vi.spyOn(plotloomApi, "getProject").mockImplementation(() => ++projectReads === 1 ? held.project.promise : Promise.resolve(current.project as any));
  vi.spyOn(plotloomApi, "getCharacterReferences").mockImplementation(() => ++referenceReads === 1 ? held.references.promise : Promise.resolve(current.references as any));
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockImplementation(() => ++proposalReads === 1 ? held.proposals.promise : Promise.resolve(current.proposals as any));
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockImplementation(() => ++workbenchReads === 1 ? held.workbench.promise : Promise.resolve(current.workbench as any));
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(castAtRevision(initial, "reopened", 1) as any);
  vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue(castAtRevision(current, "accepted", 2) as any);

  await renderProject("project");
  await flushReact();
  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  await act(async () => { button("保存重新打开的角色").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("Current live gallery evidence");
  expect(host.textContent).toContain("已接受角色 r2");

  await resolveGallery(held, initial);
  expect(host.textContent).toContain("Current live gallery evidence");
  expect(host.textContent).not.toContain("Old initial gallery evidence");
});

it("does not surface a rejected mutation from a prior subject session", async () => {
  const keeper = candidateProposal("project", "keeper"); const watcher = candidateProposal("project", "watcher");
  installResolvedGallery(galleryResponse("project", "Subject session fixture", { characters: [{ id: "keeper", name: "Mira" }, { id: "watcher", name: "Nia" }], decisions: [], referenceStates: [{ characterId: "keeper", revision: 1 }, { characterId: "watcher", revision: 1 }], proposals: [keeper.proposal, watcher.proposal], assets: [keeper.asset, watcher.asset] }));
  const selection = deferred<any>();
  vi.spyOn(plotloomApi, "selectCharacterReference").mockImplementation(() => selection.promise);

  await renderProject("project");
  await act(async () => { changeValue(host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement, "Keeper note"); });
  await flushReact();
  await act(async () => { button("选择身份参考").click(); await Promise.resolve(); });
  expect(plotloomApi.selectCharacterReference).toHaveBeenCalledTimes(1);
  await act(async () => { (host.querySelectorAll(".reference-subjects button")[1] as HTMLButtonElement).click(); await Promise.resolve(); });
  const galleryReadsBeforeOldFailure = vi.mocked(plotloomApi.getCharacterReferenceProposals).mock.calls.length;
  await act(async () => { selection.reject(new Error("old keeper mutation rejected")); await Promise.resolve(); });
  await flushReact();
  expect(vi.mocked(plotloomApi.getCharacterReferenceProposals).mock.calls).toHaveLength(galleryReadsBeforeOldFailure);
  expect(host.textContent).toContain("Nia");
  expect(host.textContent).not.toContain("old keeper mutation rejected");
});

it("rejects an old held refresh after the same subject is reopened and saved at a newer cast revision", async () => {
  const candidate = candidateProposal("project");
  const initial = galleryResponse("project", "Live session fixture", { proposals: [candidate.proposal], assets: [candidate.asset] });
  const newer = galleryResponse("project", "Live session fixture", { proposals: [candidate.proposal], assets: [candidate.asset] });
  newer.references.decisions[0].referenceRevision = 2;
  const old = galleryResponse("project", "Live session fixture", { proposals: [candidate.proposal], assets: [candidate.asset] });
  old.references.decisions[0].referenceRevision = 91;
  const heldReferences = deferred<any>(); const heldProposals = deferred<any>(); const heldWorkbench = deferred<any>();
  let phase: "initial" | "held" | "newer" = "initial";
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(initial.project as any);
  vi.spyOn(plotloomApi, "getCast").mockResolvedValue(initial.cast as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockImplementation(() => phase === "held" ? heldReferences.promise : Promise.resolve((phase === "newer" ? newer : initial).references as any));
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockImplementation(() => phase === "held" ? heldProposals.promise : Promise.resolve((phase === "newer" ? newer : initial).proposals as any));
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockImplementation(() => phase === "held" ? heldWorkbench.promise : Promise.resolve((phase === "newer" ? newer : initial).workbench as any));
  const selection = deferred<any>();
  vi.spyOn(plotloomApi, "selectCharacterReference").mockImplementation(() => selection.promise);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(castAtRevision(initial, "reopened", 1) as any);
  vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue(castAtRevision(newer, "accepted", 2) as any);

  await renderProject("project");
  await flushReact();
  const notes = host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement;
  await act(async () => { changeValue(notes, "Commit the keeper note before dispatching."); });
  await flushReact();
  await act(async () => { button("选择身份参考").click(); await Promise.resolve(); });
  expect(plotloomApi.selectCharacterReference).toHaveBeenCalledTimes(1);
  phase = "held";
  await act(async () => { selection.resolve({}); await Promise.resolve(); });
  await flushReact();

  phase = "newer";
  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  await act(async () => { button("保存重新打开的角色").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已选择身份参考 r2");

  await act(async () => {
    heldReferences.resolve(old.references); heldProposals.resolve(old.proposals); heldWorkbench.resolve(old.workbench);
    await Promise.resolve();
  });
  await flushReact();
  expect(host.textContent).toContain("已选择身份参考 r2");
  expect(host.textContent).not.toContain("已选择身份参考 r91");
});

it("rejects an old held refresh error after the same subject reaches a newer accepted cast revision", async () => {
  const candidate = candidateProposal("project");
  const initial = galleryResponse("project", "Live rejection fixture", { proposals: [candidate.proposal], assets: [candidate.asset] });
  const newer = galleryResponse("project", "Live rejection fixture", { proposals: [candidate.proposal], assets: [candidate.asset] });
  newer.references.decisions[0].referenceRevision = 2;
  const heldReferences = deferred<any>(); const heldProposals = deferred<any>(); const heldWorkbench = deferred<any>();
  let phase: "initial" | "held" | "newer" = "initial";
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(initial.project as any);
  vi.spyOn(plotloomApi, "getCast").mockResolvedValue(initial.cast as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockImplementation(() => phase === "held" ? heldReferences.promise : Promise.resolve((phase === "newer" ? newer : initial).references as any));
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockImplementation(() => phase === "held" ? heldProposals.promise : Promise.resolve((phase === "newer" ? newer : initial).proposals as any));
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockImplementation(() => phase === "held" ? heldWorkbench.promise : Promise.resolve((phase === "newer" ? newer : initial).workbench as any));
  const selection = deferred<any>();
  vi.spyOn(plotloomApi, "selectCharacterReference").mockImplementation(() => selection.promise);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(castAtRevision(initial, "reopened", 1) as any);
  vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue(castAtRevision(newer, "accepted", 2) as any);

  await renderProject("project");
  await flushReact();
  const notes = host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement;
  await act(async () => { changeValue(notes, "Commit the keeper note before dispatching."); });
  await flushReact();
  await act(async () => { button("选择身份参考").click(); await Promise.resolve(); });
  expect(plotloomApi.selectCharacterReference).toHaveBeenCalledTimes(1);
  phase = "held";
  await act(async () => { selection.resolve({}); await Promise.resolve(); });
  await flushReact();

  phase = "newer";
  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  await act(async () => { button("保存重新打开的角色").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已选择身份参考 r2");

  await act(async () => { heldReferences.reject(new Error("old held refresh rejected")); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已选择身份参考 r2");
  expect(host.textContent).not.toContain("old held refresh rejected");
  heldProposals.resolve(initial.proposals); heldWorkbench.resolve(initial.workbench);
});

it("rejects a late image-mutation error after the same subject is reopened and saved", async () => {
  const candidate = candidateProposal("project");
  const initial = galleryResponse("project", "Mutation rejection fixture", { decisions: [], proposals: [candidate.proposal], assets: [candidate.asset] });
  const newer = galleryResponse("project", "Mutation rejection fixture", { decisions: [], proposals: [candidate.proposal], assets: [candidate.asset] });
  installResolvedGallery(initial);
  const selection = deferred<any>();
  vi.spyOn(plotloomApi, "selectCharacterReference").mockImplementation(() => selection.promise);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(castAtRevision(initial, "reopened", 1) as any);
  vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue(castAtRevision(newer, "accepted", 2) as any);

  await renderProject("project");
  const notes = host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement;
  await act(async () => { changeValue(notes, "Commit the selection note before dispatching."); });
  await flushReact();
  await act(async () => { button("选择身份参考").click(); await Promise.resolve(); });
  expect(plotloomApi.selectCharacterReference).toHaveBeenCalledTimes(1);

  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  await act(async () => { button("保存重新打开的角色").click(); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已接受角色 r2");

  await act(async () => { selection.reject(new Error("old image mutation rejected")); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).toContain("已接受角色 r2");
  expect(host.textContent).not.toContain("old image mutation rejected");
  expect((host.querySelector('textarea[placeholder*="说明为何"]') as HTMLTextAreaElement).disabled).toBe(false);
});

it("remounts same-subject controls across a reopened-and-saved cast session", async () => {
  const candidate = candidateProposal("project");
  const initial = galleryResponse("project", "Local reset fixture", { decisions: [], proposals: [candidate.proposal], assets: [candidate.asset] });
  const newer = galleryResponse("project", "Local reset fixture", { decisions: [], proposals: [candidate.proposal], assets: [candidate.asset] });
  installResolvedGallery(initial);
  const preparation = deferred<any>();
  vi.spyOn(plotloomApi, "prepareCharacterReferenceProposal").mockImplementationOnce(() => preparation.promise).mockResolvedValueOnce({ proposal: candidate.proposal } as any);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(castAtRevision(initial, "reopened", 1) as any);
  vi.spyOn(plotloomApi, "saveReopenedCast").mockResolvedValue(castAtRevision(newer, "accepted", 2) as any);

  await renderProject("project");
  const direction = host.querySelector('textarea[placeholder*="描述本次外观研究"]') as HTMLTextAreaElement;
  await act(async () => { changeValue(direction, "Old session direction must be discarded."); });
  await flushReact();
  await act(async () => { button("准备手动细化 handoff").click(); await Promise.resolve(); });
  expect(plotloomApi.prepareCharacterReferenceProposal).toHaveBeenCalledTimes(1);

  await act(async () => { button("重新打开角色提案").click(); await Promise.resolve(); });
  await flushReact();
  await act(async () => { button("保存重新打开的角色").click(); await Promise.resolve(); });
  await flushReact();
  const freshDirection = host.querySelector('textarea[placeholder*="描述本次外观研究"]') as HTMLTextAreaElement;
  expect(freshDirection.disabled).toBe(false);
  expect(freshDirection.value).toBe("");
  expect((host.querySelector("select") as HTMLSelectElement).value).toBe("");

  await act(async () => { changeValue(freshDirection, "Fresh session direction dispatches."); });
  await flushReact();
  await act(async () => { button("准备手动细化 handoff").click(); await Promise.resolve(); });
  expect(plotloomApi.prepareCharacterReferenceProposal).toHaveBeenCalledTimes(2);
  await act(async () => { preparation.resolve({ assignment: "old assignment must not appear" }); await Promise.resolve(); });
  await flushReact();
  expect(host.textContent).not.toContain("old assignment must not appear");
  expect((host.querySelector('textarea[placeholder*="描述本次外观研究"]') as HTMLTextAreaElement).disabled).toBe(false);
});

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
  expect(signals.get("old-project")).toHaveLength(4);
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
