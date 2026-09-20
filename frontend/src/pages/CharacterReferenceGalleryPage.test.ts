import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { plotloomApi } from "../api";
import { CharacterReferenceGalleryPage } from "./CharacterReferenceGalleryPage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

async function flush() {
  await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 0)); });
}

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("recovers a failed hero when its preserved component receives another subject identity", async () => {
  const original = { id: "same-asset", projectId: "project", originalHash: "original", displayHash: "display", mimeType: "image/png", byteSize: 20, width: 64, height: 48, createdAt: "2026-09-20T00:00:00Z", provenance: null };
  const decision = (id: string, characterId: string) => ({ id, projectId: "project", characterId, referenceRevision: 1, characterContext: {}, characterContextHash: id, primaryAssetId: original.id, complementaryAssetIds: [], assetHashes: [], reviewer: "reviewer", notes: "test", current: true, revokedAt: null, revokedBy: null, revocationReason: null, createdAt: "2026-09-20T00:00:00Z" });
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ id: "project", brief: { title: "Identity reset fixture" } } as any);
  vi.spyOn(plotloomApi, "getCast").mockResolvedValue({ candidate: null, acceptedCast: { revision: 1, candidateJobId: "cast", contentHash: "cast", binding: {}, acceptedAt: "2026-09-20T00:00:00Z", cast: { characters: [{ id: "keeper", name: "Mira" }, { id: "watcher", name: "Nia" }] }, consumerMappings: [{ castCharacterId: "keeper", consumerCharacterId: "keeper" }, { castCharacterId: "watcher", consumerCharacterId: "watcher" }] }, status: "accepted", staleReasons: [] } as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockResolvedValue({ states: [], decisions: [decision("keeper", "keeper"), decision("watcher", "watcher")] } as any);
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: true, proposals: [] } as any);
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue({ assets: [original], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], characterReferences: { states: [], decisions: [] }, samePersonReviews: { revision: 0, reviews: [] }, previews: [] } as any);

  window.history.replaceState({}, "", "/?view=character-reference-review&project=project");
  await act(async () => root.render(createElement(CharacterReferenceGalleryPage)));
  await flush();
  const firstHero = host.querySelector('[data-testid="reference-selected-hero"]')!;
  await act(async () => firstHero.querySelector("img")?.dispatchEvent(new Event("error")));
  expect(firstHero.textContent).toContain("当前已选择的身份参考图像不可用");

  await act(async () => (host.querySelectorAll(".reference-subjects button")[1] as HTMLButtonElement).click());
  await flush();
  const secondHero = host.querySelector('[data-testid="reference-selected-hero"]')!;
  expect(secondHero.querySelector("img")).not.toBeNull();
  expect(secondHero.textContent).not.toContain("图像不可用");
});
