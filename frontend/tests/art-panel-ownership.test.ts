import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { specialistsApi } from "../src/features/specialists/api";
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

it("uses creator-confirmation wording and selection labels for accepted Art", async () => {
  vi.spyOn(plotloomApi, "getArt").mockResolvedValue(artState("old"));
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [deliveredStudy] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({
    states: [{ subjectType: "scene", subjectId: "S01", revision: 0, activeDecisionId: null, current: false }], decisions: [],
  });

  await act(async () => { root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })); });

  expect(host.textContent).toContain("已确认美术设定 r1");
  expect(host.querySelector('section[aria-label="准备美术设定候选"]')?.textContent).toContain("准备新的美术候选（可选）");
  expect(host.textContent).toContain("新候选需要单独审核并确认，不会自动替换已有设定");
  expect(host.textContent).toContain("按已确认的美术设定生成图片");
  expect([...host.querySelectorAll("button")].some(button => button.textContent === "选用这张环境参考图")).toBe(true);
});

it("settles a deferred F3B send after unmount without refresh, assignment, or error publication", async () => {
  const copied = deferred<{ proposal: ArtReferenceProposal; assignment: string; packagePath: string; deliveryPath: string }>();
  const getArt = vi.spyOn(plotloomApi, "getArt").mockImplementation(async (projectId) => artState(projectId));
  const getStudies = vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [study] });
  const getDecisions = vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  vi.spyOn(specialistsApi, "sendArtImage").mockReturnValue(copied.promise);

  await act(async () => { root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })); });
  const copy = [...host.querySelectorAll("button")].find((button) => button.textContent === "发送给图像生成助手");
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
  const choose = [...host.querySelectorAll("button")].find((button) => button.textContent === "选用这张环境参考图");
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

it("guides recovery of a retained dirty Art draft before a newer accepted result", async () => {
  let current = { ...artState("old"), status: "reopened" as ArtReviewState["status"] };
  vi.spyOn(plotloomApi, "getArt").mockImplementation(async () => current);
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  const onContinue = vi.fn();
  await act(async () => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false, refreshToken: 1, onContinue })));
  const editor = host.querySelector<HTMLTextAreaElement>("details.art-json-editor textarea:not(:disabled)")!;
  const dirty = `${editor.value}\n `;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(editor, dirty);
    editor.dispatchEvent(new Event("input", { bubbles: true }));
  });
  expect(host.querySelector(".stage-guide")?.textContent).toContain("先保存或明确舍弃美术修改");
  current = { ...current, status: "accepted", acceptedArt: { ...current.acceptedArt!, revision: 2, contentHash: "new-head" } };
  await act(async () => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false, refreshToken: 2, onContinue })));
  const guide = host.querySelector(".stage-guide")!;
  expect(guide.textContent).toContain("保留了基于旧版本的美术草稿");
  expect(guide.textContent).not.toContain("可继续编写剧本");
  expect(host.querySelector<HTMLTextAreaElement>('[aria-label="保留的美术草稿"]')?.value).toBe(dirty);
  const continuation = [...host.querySelectorAll("button")].find(button => button.textContent === "继续：剧本")!;
  expect(continuation.disabled).toBe(true);
  const discard = [...host.querySelectorAll("button")].find(button => button.textContent === "舍弃美术草稿")!;
  await act(async () => discard.click());
  expect(guide.textContent).toContain("可继续编写剧本");
  expect(continuation.disabled).toBe(false);
  expect(onContinue).not.toHaveBeenCalled();
});

it.each(["stale", "reopened", "prepared", "candidate_ready"] as const)("does not authorize reference selection from retained Art while %s", async (status) => {
  vi.spyOn(plotloomApi, "getArt").mockResolvedValue({ ...artState("old"), status });
  // A retained proposal's flag alone must not confer current Art authority.
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [deliveredStudy] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  const choose = vi.spyOn(plotloomApi, "createArtReferenceDecision");
  await act(async () => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })));
  const select = [...host.querySelectorAll("button")].find(button => button.textContent === "选用这张环境参考图")!;
  expect(select.disabled).toBe(true);
  await act(async () => select.click());
  expect(choose).not.toHaveBeenCalled();
  expect(host.querySelector('img[alt="Held scene 当前查看图片"]')).not.toBeNull();
  expect(host.textContent).toContain("查看保留的参考图片");
  expect(host.textContent).toContain("暂不能准备、发送或选用参考图");
  expect([...host.querySelectorAll("button")].find(button => button.textContent === "修改要求，再生成一张")!.disabled).toBe(true);
});

it("keeps reference selection blocked while a retained accepted head is being refreshed", async () => {
  const pending = deferred<ArtReviewState>();
  const getArt = vi.spyOn(plotloomApi, "getArt").mockResolvedValue(artState("old"));
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [deliveredStudy] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  const render = (token: number) => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false, refreshToken: token }));
  const select = () => [...host.querySelectorAll("button")].find(button => button.textContent === "选用这张环境参考图")!;
  await act(async () => render(1));
  expect(select().disabled).toBe(false);
  getArt.mockReturnValueOnce(pending.promise);
  await act(async () => render(2));
  expect(select().disabled).toBe(true);
  await act(async () => { pending.resolve({ ...artState("old"), status: "stale" }); await pending.promise; });
  expect(select().disabled).toBe(true);
});

it("keeps reference selection blocked after a failed refresh until successful revalidation", async () => {
  const getArt = vi.spyOn(plotloomApi, "getArt").mockResolvedValue(artState("old"));
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [deliveredStudy] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  const render = (token: number) => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false, refreshToken: token }));
  const button = (label: string) => [...host.querySelectorAll("button")].find(entry => entry.textContent === label)!;
  await act(async () => render(1));
  getArt.mockRejectedValueOnce(new Error("Temporary read failure"));
  await act(async () => render(2));
  expect(button("选用这张环境参考图").disabled).toBe(true);
  await act(async () => button("重试加载美术参考").click());
  expect(button("选用这张环境参考图").disabled).toBe(false);
});

it("allows another still-current older candidate without requiring it to be the newest proposal", async () => {
  vi.spyOn(plotloomApi, "getArt").mockResolvedValue(artState("old"));
  vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: true, proposals: [study, { ...deliveredStudy, id: "older-study" }] });
  vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ states: [], decisions: [] });
  await act(async () => root.render(createElement(ArtPanel, { projectId: "old", readOnly: false })));
  expect([...host.querySelectorAll("button")].find(button => button.textContent === "选用这张环境参考图")!.disabled).toBe(false);
});
