import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { CharacterReferenceReviewPanel } from "../src/pages/CharacterReferenceGalleryPage";
import type { CastReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const owner = { current: "session" };
const castState: CastReviewState = { acceptedReviewState: { status: "current", staleReasons: [] },
  status: "accepted", staleReasons: [], candidate: null,
  acceptedCast: {
    revision: 1, candidateJobId: "cast", contentHash: "cast", acceptedAt: "2026-10-08T00:00:00Z", reportAvailable: false, differsFromDelivery: null,
    binding: { sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "sections", graphRevision: 1, graphContentHash: "graph", sectionIds: ["opening"] },
    cast: { characters: [{ id: "keeper", name: "Mira", persona: { personality: ["Careful"], appearance: "Beacon coat" } }] },
    consumerMappings: [{ castCharacterId: "keeper", consumerCharacterId: "keeper" }],
  },
};
const props = { projectId: "project", readOnly: false, castState, castSession: "session", castSessionOwner: owner, castTransitionPending: false };

beforeEach(() => {
  owner.current = "session";
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ id: "project", brief: { title: "Gallery fixture" } } as any);
  vi.spyOn(plotloomApi, "getCharacterReferences").mockResolvedValue({ decisions: [], states: [] });
  vi.spyOn(plotloomApi, "getCharacterReferenceProposals").mockResolvedValue({ configured: true, proposals: [] });
  vi.spyOn(plotloomApi, "getVisualWorkbench").mockResolvedValue({ assets: [] } as any);
  vi.spyOn(plotloomApi, "getImportedCharacterAppearances").mockResolvedValue({ appearances: [] });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers(); });
async function render(readOnly = false) { await act(async () => root.render(createElement(CharacterReferenceReviewPanel, { ...props, readOnly }))); }
function retryButton() { return [...host.querySelectorAll("button")].find(button => button.textContent?.includes("重新读取角色参考"))!; }
function exportedProposal() { return { id: "pending", characterId: "keeper", current: true, state: "exported", deliveries: [], parentCandidateAssetId: null, requestHash: "request", request: { frozenSnapshot: { visualDirection: "Retain the coat" } } } as any; }

it("distinguishes failed reads from empty images and retries only reads with a pending guard", async () => {
  const references = vi.mocked(plotloomApi.getCharacterReferences);
  let settle!: (value: { decisions: []; states: [] }) => void;
  const held = new Promise<{ decisions: []; states: [] }>(resolve => { settle = resolve; });
  references.mockRejectedValueOnce(new Error("gallery read failed")).mockImplementationOnce(() => held);
  const prepare = vi.spyOn(plotloomApi, "prepareCharacterReferenceProposal");
  const send = vi.spyOn(plotloomApi, "sendCharacterReferenceProposal");
  const select = vi.spyOn(plotloomApi, "selectCharacterReference");
  await render();
  expect(host.textContent).toContain("gallery read failed");
  expect(host.querySelector('[data-testid="reference-no-image"]')).toBeNull();
  await act(async () => retryButton().click());
  expect(retryButton().disabled).toBe(true);
  expect(references).toHaveBeenCalledTimes(2);
  await act(async () => settle({ decisions: [], states: [] }));
  expect(host.querySelector('[data-testid="reference-no-image"]')).not.toBeNull();
  expect(host.querySelector(".appearance-viewer-heading")?.textContent).toContain("尚无参考图片");
  expect(host.querySelector(".appearance-viewer-heading")?.textContent).not.toContain("当前身份参考");
  expect(host.textContent).not.toContain("gallery read failed");
  expect(prepare).not.toHaveBeenCalled(); expect(send).not.toHaveBeenCalled(); expect(select).not.toHaveBeenCalled();
});

it("keeps known content and local inputs on a failed refresh, blocking mutations until recovery", async () => {
  vi.useFakeTimers();
  vi.mocked(plotloomApi.getCharacterReferenceProposals).mockResolvedValue({ configured: true, proposals: [exportedProposal()] });
  vi.spyOn(plotloomApi, "refreshCharacterReferenceProposal").mockResolvedValue({ state: "delivery_accepted" } as any);
  await render();
  const input = host.querySelector('textarea[placeholder*="描述希望保留"]')! as HTMLTextAreaElement;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(input, "Unsaved appearance idea");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  vi.mocked(plotloomApi.getCharacterReferences).mockRejectedValueOnce(new Error("refresh failed"));
  await act(async () => vi.advanceTimersByTimeAsync(3000));
  expect(host.textContent).toContain("refresh failed");
  expect(host.textContent).toContain("已确认角色设定 r1");
  expect(host.querySelector('textarea[placeholder*="描述希望保留"]')).toBe(input);
  expect(input.value).toBe("Unsaved appearance idea");
  expect(input.disabled).toBe(true);
  await act(async () => retryButton().click());
  expect(input.disabled).toBe(false);
  expect(input.value).toBe("Unsaved appearance idea");
});

it("read-only guidance never invites mutations or background delivery observation", async () => {
  vi.useFakeTimers();
  vi.mocked(plotloomApi.getCharacterReferenceProposals).mockResolvedValue({ configured: true, proposals: [exportedProposal()] });
  const observe = vi.spyOn(plotloomApi, "refreshCharacterReferenceProposal");
  await render(true);
  expect(host.textContent).toContain("此项目为只读");
  expect(host.textContent).not.toContain("可以审阅、选择、准备并发送新提案");
  await act(async () => vi.advanceTimersByTimeAsync(6000));
  expect(observe).not.toHaveBeenCalled();
});

it("releases manual retry pending when a held observation supersedes its read", async () => {
  vi.useFakeTimers();
  let finishObservation!: (value: any) => void;
  let failRetry!: (reason: Error) => void;
  const observation = new Promise<any>(resolve => { finishObservation = resolve; });
  const manualRead = new Promise<never>((_, reject) => { failRetry = reject; });
  vi.mocked(plotloomApi.getCharacterReferenceProposals).mockResolvedValue({ configured: true, proposals: [exportedProposal()] });
  const observe = vi.spyOn(plotloomApi, "refreshCharacterReferenceProposal")
    .mockImplementationOnce(() => observation)
    .mockResolvedValue({ state: "delivery_accepted" } as any);
  const reads = vi.mocked(plotloomApi.getCharacterReferences)
    .mockResolvedValueOnce({ decisions: [], states: [] })
    .mockRejectedValueOnce(new Error("first background read failed"))
    .mockImplementationOnce(() => manualRead)
    .mockRejectedValueOnce(new Error("newer background read failed"));
  await render();
  await act(async () => vi.advanceTimersByTimeAsync(3000));
  await act(async () => vi.advanceTimersByTimeAsync(3000));
  expect(host.textContent).toContain("first background read failed");
  await act(async () => retryButton().click());
  expect(retryButton().disabled).toBe(true);
  await act(async () => finishObservation({ state: "delivery_accepted" }));
  expect(host.textContent).toContain("newer background read failed");
  await act(async () => failRetry(new Error("superseded manual read failed")));
  expect(host.textContent).toContain("newer background read failed");
  expect(host.textContent).not.toContain("superseded manual read failed");
  expect(retryButton().disabled).toBe(false);
  expect(observe).toHaveBeenCalledTimes(2);
  expect(reads).toHaveBeenCalledTimes(4);
});

it("ignores a retry that completes after its cast session is invalidated", async () => {
  let settle!: (value: { decisions: []; states: [] }) => void;
  const held = new Promise<{ decisions: []; states: [] }>(resolve => { settle = resolve; });
  vi.mocked(plotloomApi.getCharacterReferences).mockRejectedValueOnce(new Error("failed current read")).mockImplementationOnce(() => held);
  await render();
  await act(async () => retryButton().click());
  owner.current = "new-session";
  await act(async () => settle({ decisions: [], states: [] }));
  expect(host.textContent).toContain("failed current read");
  expect(host.querySelector('[data-testid="reference-no-image"]')).toBeNull();
});
