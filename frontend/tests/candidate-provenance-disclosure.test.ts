import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { CandidateCard } from "../src/features/media/assets/MediaCandidates";
import { CharactersPage } from "../src/pages/CharactersPage";
import type { ManagedAsset } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

const declarations: Array<[string, ManagedAsset["provenance"]]> = [
  ["known", { origin: "persisted known source", rights: "known", rightsNote: "Declared license, not creator approval", declaredAdditions: [] }],
  ["unknown", { origin: "persisted generated source", rights: "unknown", rightsNote: null, declaredAdditions: [] }],
  ["absent", null],
  ["empty source", { origin: "", rights: "unknown", rightsNote: "Retained declaration with no source text", declaredAdditions: [] }],
];
function asset(projectId: string, provenance: ManagedAsset["provenance"]): ManagedAsset {
  return { id: `${projectId}-asset`, projectId, originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-10-07T00:00:00Z", provenance };
}
function row(details: Element, label: string) {
  return [...details.querySelectorAll("dt")].find(e => e.textContent === label)?.nextElementSibling?.textContent;
}
function assertDeclaration(details: Element, expected: ManagedAsset) {
  expect(row(details, "资产")).toBe(expected.id);
  expect(row(details, "来源")).toBe(expected.provenance?.origin || "来源信息不可用");
  expect(row(details, "权利")).toBe(expected.provenance?.rights ?? "权利信息不可用");
  expect(row(details, "权利说明")).toBe(expected.provenance?.rightsNote ?? undefined);
}

it.each(declarations)("shot candidate displays %s declaration without selection and retains exact identity on reopen", async (_, provenance) => {
  const onPick = vi.fn(); const onKeep = vi.fn();
  const render = async (candidate: ManagedAsset) => act(async () => root.render(createElement(CandidateCard, { asset: candidate, projectId: candidate.projectId, selected: false, kept: false, onPick, onKeep })));
  const original = asset("A", provenance);
  await render(original);
  const details = host.querySelector("details")!;
  await act(async () => details.querySelector("summary")!.click());
  assertDeclaration(details, original);
  expect(onPick).not.toHaveBeenCalled(); expect(onKeep).not.toHaveBeenCalled();
  const other = asset("B", null);
  await render(other); assertDeclaration(host.querySelector("details")!, other);
  expect(host.querySelector("img")!.getAttribute("src")).toContain("/B/managed-assets/B-asset/");
  await act(async () => root.render(null));
  await render(original); assertDeclaration(host.querySelector("details")!, original);
  expect(host.textContent).not.toContain("B-asset");
});

function installGallery(provenance: ManagedAsset["provenance"]) {
  vi.spyOn(plotloomApi, "getProject").mockImplementation(async id => ({ id, brief: { title: id } }) as never);
  vi.spyOn(plotloomApi, "getCast").mockImplementation(async id => ({ candidate: null, status: "accepted", staleReasons: [], acceptedCast: { revision: 1, candidateJobId: "cast", contentHash: "cast", binding: {}, cast: { characters: [{ id: "keeper", name: "Lin", persona: { personality: ["Careful"], appearance: "Plain coat" } }] }, consumerMappings: [{ castCharacterId: "keeper", consumerCharacterId: "keeper" }] } }) as never);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockResolvedValue({ states: [], decisions: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockImplementation(async id => {
    const current = asset(id, id === "A" ? provenance : null);
    return { configured: true, proposals: [{ id: `${id}-proposal`, projectId: id, characterId: "keeper", current: true, state: "delivered", parentCandidateAssetId: null, requestHash: "request", request: {}, deliveries: [{ id: `${id}-delivery`, state: "accepted", candidates: [{ id: `${id}-candidate`, assetId: current.id, asset: current, outputHash: "output", role: "original" }] }] }] } as never;
  });
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockImplementation(async id => ({ assets: [asset(id, id === "A" ? provenance : null)], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] }) as never);
  vi.spyOn(plotloomApi, "getImportedCharacterAppearances").mockResolvedValue({ appearances: [] });
}
async function renderCharacters(projectId: string) {
  await act(async () => root.render(createElement(CharactersPage, { projectId, readOnly: false })));
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
}
it.each(declarations)("native Character candidate displays %s declaration on the viewed asset, not another project", async (_, provenance) => {
  installGallery(provenance);
  await renderCharacters("A");
  const details = () => host.querySelector('[data-testid="appearance-viewer"] details')!;
  await act(async () => details().querySelector("summary")!.click());
  assertDeclaration(details(), asset("A", provenance));
  expect(row(details(), "提案")).toBe("A-proposal");
  await renderCharacters("B"); assertDeclaration(details(), asset("B", null));
  await act(async () => root.render(null));
  await renderCharacters("A"); assertDeclaration(details(), asset("A", provenance));
  expect(details().textContent).not.toContain("B-proposal");
});
