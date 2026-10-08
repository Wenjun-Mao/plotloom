const mediaOwnerIds = new Set([
  "shot-workbench", "shot-original", "shot-segment", "shot-story-preview",
  "shot-character-references", "shot-keyframe-review",
]);

/** Navigation must reveal the owning disclosure before scrolling its content. */
export function revealMediaOwner(id: string, behavior: ScrollBehavior = "smooth") {
  if (!mediaOwnerIds.has(id)) return;
  const target = document.getElementById(id);
  if (!target) return;
  for (let owner: HTMLElement | null = target; owner; owner = owner.parentElement) {
    if (owner instanceof HTMLDetailsElement) owner.open = true;
  }
  requestAnimationFrame(() => {
    if (target.isConnected) target.scrollIntoView({ behavior, block: "start" });
  });
}
