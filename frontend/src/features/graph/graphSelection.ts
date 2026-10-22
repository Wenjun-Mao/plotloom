/** Selection is a project presentation preference, never an authored mutation. */
export function readGraphSelection(projectId: string): string | null {
  try {
    const value = JSON.parse(localStorage.getItem(`plotloom:graph-selection:v1:${projectId}`) || "null");
    return typeof value === "string" ? value : null;
  } catch { return null; }
}
export function storeGraphSelection(projectId: string, identity: string | null) {
  try { localStorage.setItem(`plotloom:graph-selection:v1:${projectId}`, JSON.stringify(identity)); }
  catch { /* Optional presentation storage cannot block story editing. */ }
}
