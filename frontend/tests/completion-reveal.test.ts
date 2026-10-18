import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { useCompletionReveal, revealWorkspaceTarget } from "../src/app/workspace/completionReveal";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
function rect(element: HTMLElement, top: number, bottom: number) { vi.spyOn(element, "getBoundingClientRect").mockReturnValue({ top, bottom, width: 1000, height: bottom-top } as DOMRect); }
it("reveals below the actual guide and honors reduced motion and keyboard focus", () => {
  document.body.innerHTML = '<div class="topbar"></div><div class="recommended-workflow-guide"></div><section id="target"></section>';
  const target = document.getElementById("target")!;
  rect(document.querySelector(".topbar")!,0,60); rect(document.querySelector(".recommended-workflow-guide")!,60,180); rect(target,500,550);
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches:true } as MediaQueryList)));
  const scroll = vi.spyOn(window,"scrollBy").mockImplementation(() => {});
  revealWorkspaceTarget(target);
  expect(scroll).toHaveBeenCalledExactlyOnceWith({top:308,behavior:"auto"}); expect(document.activeElement).toBe(target);
});
it("owns one foreground reveal and clears it on identity/navigation, hidden tabs and edits", async () => {
  const host = document.createElement("div"); document.body.append(host);
  const target = document.createElement("section"); target.id="target"; document.body.append(target);
  const root=createRoot(host); let owner!:ReturnType<typeof useCompletionReveal>;
  function Probe({id,blocked}:{id:string;blocked:boolean}) { owner=useCompletionReveal(id,blocked); return null; }
  vi.spyOn(window,"requestAnimationFrame").mockImplementation(callback=>{callback(0);return 1;});
  vi.spyOn(document,"visibilityState","get").mockReturnValue("visible");
  const scroll=vi.spyOn(window,"scrollBy").mockImplementation(()=>{});
  try {
    await act(async()=>root.render(createElement(Probe,{id:"project:run:route",blocked:false})));
    owner.reveal("target"); expect(scroll).not.toHaveBeenCalled();
    owner.arm(); owner.reveal("target"); owner.reveal("target"); expect(scroll).toHaveBeenCalledTimes(1);
    owner.arm(); await act(async()=>root.render(createElement(Probe,{id:"project:other-run:route",blocked:false}))); owner.reveal("target"); expect(scroll).toHaveBeenCalledTimes(1);
    owner.arm(); vi.spyOn(document,"visibilityState","get").mockReturnValue("hidden"); document.dispatchEvent(new Event("visibilitychange"));
    vi.spyOn(document,"visibilityState","get").mockReturnValue("visible"); owner.reveal("target"); expect(scroll).toHaveBeenCalledTimes(1);
    owner.arm(); window.dispatchEvent(new HashChangeEvent("hashchange")); owner.reveal("target"); expect(scroll).toHaveBeenCalledTimes(1);
    owner.arm(); await act(async()=>root.render(createElement(Probe,{id:"project:other-run:route",blocked:true}))); owner.reveal("target"); expect(scroll).toHaveBeenCalledTimes(1);
  } finally { await act(async()=>root.unmount()); }
});
