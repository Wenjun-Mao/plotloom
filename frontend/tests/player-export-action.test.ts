import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PlayerExportAction } from "../src/features/media/PlayerExportAction";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const NativeURL = URL;
let root: Root, host: HTMLDivElement;
const create = vi.fn(() => "blob:export"), revoke = vi.fn();
beforeEach(() => {
  vi.useFakeTimers(); create.mockClear(); revoke.mockClear();
  vi.stubGlobal("URL", class extends NativeURL { static createObjectURL = create; static revokeObjectURL = revoke; });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.runOnlyPendingTimers(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("downloads using the exact project-owned intro, ending cards and bindings", async () => {
  const presentation = { version: 1, admissionId: "admission", gameId: "last-projection", intro: "作者的开场文字。",
    endingCards: { e01: { title: "独自交接", text: "作者的结束卡全文。" } },
    nodeBindings: { E01: "e01" }, edgeBindings: {}, slotBindings: { opening: "shot-1" } };
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify(presentation), { headers: { "Content-Type": "application/json" } }))
    .mockResolvedValueOnce(new Response(new Uint8Array([80, 75, 3, 4]), { headers: { "Content-Type": "application/zip" } }));
  await act(async () => root.render(createElement(PlayerExportAction, { projectId: "project", disabled: false })));
  await act(async () => host.querySelector("button")!.click());
  expect(fetcher).toHaveBeenNthCalledWith(1, "/api/v2/projects/project/player-export-presentation");
  expect(fetcher).toHaveBeenNthCalledWith(2, "/api/v2/projects/project/player-exports", expect.objectContaining({ method: "POST", body: JSON.stringify(presentation) }));
  expect(create).toHaveBeenCalledOnce();
  expect(host.textContent).toContain("游戏已导出");
});

it("cannot send or download an old project's presentation after switching projects", async () => {
  let finish!: (response: Response) => void;
  const pending = new Promise<Response>(resolve => { finish = resolve; });
  const fetcher = vi.spyOn(globalThis, "fetch").mockReturnValueOnce(pending);
  await act(async () => root.render(createElement(PlayerExportAction, { projectId: "old", disabled: false })));
  await act(async () => host.querySelector("button")!.click());
  await act(async () => root.render(createElement(PlayerExportAction, { projectId: "new", disabled: false })));
  await act(async () => finish(new Response(JSON.stringify({ admissionId: "old-admission", gameId: "old" }))));
  expect(fetcher).toHaveBeenCalledOnce(); expect(create).not.toHaveBeenCalled();
  expect(host.textContent).not.toContain("游戏已导出");
});
