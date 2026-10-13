import { act, createElement as h } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { AutopilotWorkspace } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { CharacterReferenceReviewPanel } from "../src/pages/CharacterReferenceGalleryPage";
import { ArtReferenceGallery } from "../src/pages/ArtReferenceGallery";
import { CharacterReferencesPanel } from "../src/features/media/references/CharacterReferencesPanel";
import type { CastReviewState } from "../src/types";
import { fixtureRun } from "./autopilot-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());

it.each(["ai", "manual", "unknown", "different-hash", "different-revision"])("reference headings preserve exact %s provenance and neutral membership", async kind => {
  const read = vi.spyOn(autopilotApi, "current");
  if (kind === "manual") read.mockResolvedValue(null);
  else if (kind === "unknown") read.mockRejectedValue(new Error("unreadable provenance"));
  else read.mockResolvedValue({ ...fixtureRun, state: "running", phase: "first-frames", checkpoints: ["characters", "art"].map(operationKey => ({ operationKey, state: "adopted", evidence: { owner: operationKey, result: { revision: kind === "different-revision" ? 2 : 1, contentHash: kind === "different-hash" ? "other" : `${operationKey}-hash` } } })) });
  const cast = { revision: 1, contentHash: "characters-hash", cast: { characters: [{ id: "lin", name: "林遥" }] }, consumerMappings: [{ castCharacterId: "lin", consumerCharacterId: "lin" }] };
  const state = { status: "accepted", acceptedCast: cast, candidate: null, staleReasons: [], acceptedReviewState: { status: "current", staleReasons: [] } } as unknown as CastReviewState;
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ brief: { title: "Fixture" } } as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockResolvedValue({ states: [], decisions: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ proposals: [] } as any);
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue({ assets: [] } as any);
  vi.spyOn(plotloomApi, "getImportedCharacterAppearances").mockResolvedValue({ appearances: [] });
  const prepare = vi.spyOn(plotloomApi, "prepareCharacterReferenceProposal");
  const select = vi.spyOn(plotloomApi, "selectCharacterReference");
  const control = vi.spyOn(autopilotApi, "control");
  const session = { current: "fixture" };
  const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
  try {
    await act(async () => root.render(h(AutopilotWorkspace, { projectId: "fixture", revision: 1, readOnly: false, onChanged: async () => {}, onVideo: () => {}, children: [
      h(CharacterReferenceReviewPanel, { key: "cast", projectId: "fixture", readOnly: false, castState: state, castSession: "fixture", castSessionOwner: session, castTransitionPending: false }),
      h(ArtReferenceGallery, { key: "art", projectId: "fixture", art: { scenes: [{ id: "S01", name: "房间" }], props: [] }, acceptedRevision: 1, acceptedContentHash: "art-hash", acceptedArtCurrent: true, studies: [], decisions: [], decisionStates: [], readOnly: false, busy: false, setAssignment: () => {}, refresh: async () => {} }),
    ] })));
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const gallery = host.querySelector('[data-testid="character-reference-gallery"]')!;
    const art = host.querySelector('[data-testid="art-reference-studies"]')!;
    const label = kind === "ai" ? "AI 已采用" : kind === "manual" ? "已确认" : "已采用 · 来源待核实";
    expect(gallery.querySelector(".reference-gallery-cast-state strong")?.textContent).toBe(`${label}角色设定 r1`);
    expect(art.querySelector("header strong")?.textContent).toBe(`按${label}的美术设定生成图片`);
    expect(gallery.querySelector('nav[aria-label="角色主体"]')?.textContent).toContain("林遥设定中的角色");
    expect(gallery.querySelector('nav[aria-label="角色主体"]')?.textContent).not.toContain("已确认角色");
    expect(prepare).not.toHaveBeenCalled(); expect(select).not.toHaveBeenCalled(); expect(control).not.toHaveBeenCalled();
    expect(JSON.stringify(cast)).toContain("characters-hash");
  } finally { await act(async () => root.unmount()); host.remove(); }
});

it("current reference metadata preserves its real reviewer and only states the cast binding", async () => {
  const decision = { characterId: "lin", current: true, referenceRevision: 1, primaryAssetId: "primary", complementaryAssetIds: [], assetHashes: [], reviewer: "Actual human", notes: "Genuine reference review", characterContext: { acceptedCast: { revision: 1, contentHash: "c".repeat(64), castCharacterId: "lin" } } };
  const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
  try {
    await act(async () => root.render(h(CharacterReferencesPanel, { bible: { characters: [{ id: "lin", name: "林遥" }] } as any, workbench: { assets: [] } as any, assetById: new Map(), referenceStateByCharacter: new Map(), currentReferenceByCharacter: new Map([["lin", decision]]) as any, readOnly: true, busy: false, mediaReadPhase: "ready", onSelectReference: () => {}, onRevokeReference: () => {}, form: { characterId: "lin", primaryAssetId: "", complementaryAssetIds: [], reviewer: "Actual human", notes: "", setCharacterId: () => {}, setPrimaryAssetId: () => {}, setComplementaryAssetIds: () => {}, setReviewer: () => {}, setNotes: () => {} } })));
    expect(host.querySelector('[data-testid="cast-linked-reference-lin"]')?.textContent).toContain("角色设定绑定 · lin · r1");
    expect(host.textContent).not.toContain("已确认角色");
    expect(host.textContent).toContain("Actual human");
    expect(host.textContent).toContain("Genuine reference review");
  } finally { await act(async () => root.unmount()); host.remove(); }
});
