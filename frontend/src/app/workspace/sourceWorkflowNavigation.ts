export const sourceWorkflowTargets = ["source", "art", "script", "storyboard-review"] as const;

export type SourceWorkflowTarget = typeof sourceWorkflowTargets[number];

export function sourceWorkflowTarget(value: string): SourceWorkflowTarget | undefined {
  return (sourceWorkflowTargets as readonly string[]).includes(value) ? value as SourceWorkflowTarget : undefined;
}

export function sourceWorkflowHref(projectId: string, target: SourceWorkflowTarget) {
  const query = new URLSearchParams({ project: projectId, stage: "source" });
  return `?${query.toString()}#${encodeURIComponent(target)}`;
}

export function workspaceHref(projectId: string, stage: string) {
  return `?${new URLSearchParams({ project: projectId, stage }).toString()}`;
}

export function viewHref(projectId: string, view: "play" | "story-prototype") {
  return `?${new URLSearchParams({ project: projectId, view }).toString()}`;
}
