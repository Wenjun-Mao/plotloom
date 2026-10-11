/** The visible sticky chrome owns space above the workspace, including its guide. */
export function workspaceHeaders(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>(".topbar, .recommended-workflow-guide")];
}

export function workspaceViewportTop(): number {
  return Math.max(0, ...workspaceHeaders().map(element => {
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight
      ? Math.min(window.innerHeight, rect.bottom) : 0;
  }));
}
