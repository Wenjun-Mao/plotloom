import { useEffect, useRef } from "react";
import { workspaceViewportTop } from "./workspaceViewport";

export function revealWorkspaceTarget(target: HTMLElement, focus = true, requestedBehavior: ScrollBehavior = "smooth") {
  for (let owner: HTMLElement | null = target; owner; owner = owner.parentElement) {
    if (owner instanceof HTMLDetailsElement) owner.open = true;
  }
  const behavior = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : requestedBehavior;
  window.scrollBy({ top: target.getBoundingClientRect().top - workspaceViewportTop() - 12, behavior });
  if (focus) { target.tabIndex = -1; target.focus({ preventScroll: true }); }
}

/** A foreground command owns one reveal; persisted/polled state alone owns none. */
export function useCompletionReveal(identity: string, blocked = false) {
  const epoch = useRef(0);
  const intent = useRef<{ identity: string; url: string } | null>(null);
  const current = useRef({ identity, blocked }); current.current = { identity, blocked };
  useEffect(() => { intent.current = null; epoch.current += 1; }, [identity]);
  useEffect(() => {
    const clear = () => { intent.current = null; epoch.current += 1; };
    const visibility = () => { if (document.visibilityState !== "visible") clear(); };
    window.addEventListener("hashchange", clear); window.addEventListener("popstate", clear); window.addEventListener("pagehide", clear);
    document.addEventListener("visibilitychange", visibility);
    return () => { window.removeEventListener("hashchange", clear); window.removeEventListener("popstate", clear); window.removeEventListener("pagehide", clear); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  return {
    arm: () => { intent.current = document.visibilityState === "visible" ? { identity: current.current.identity, url: window.location.href } : null; },
    clear: () => { intent.current = null; epoch.current += 1; },
    reveal: (id: string) => {
      const pending = intent.current; intent.current = null;
      if (!pending) return;
      const expectedEpoch = epoch.current;
      requestAnimationFrame(() => {
        const active = document.activeElement;
        if (expectedEpoch !== epoch.current || pending.identity !== current.current.identity || pending.url !== window.location.href || current.current.blocked
          || document.visibilityState !== "visible" || document.querySelector("dialog[open]")
          || active instanceof HTMLElement && (active.matches("input, textarea, select") || active.isContentEditable)) return;
        const target = document.getElementById(id);
        if (target) revealWorkspaceTarget(target);
      });
    },
  };
}
