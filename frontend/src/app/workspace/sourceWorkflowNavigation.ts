export const sourceWorkflowTargets = ["source", "art", "script", "storyboard-review"] as const;

export type SourceWorkflowTarget = typeof sourceWorkflowTargets[number];

const sourceWorkflowLabels: Record<SourceWorkflowTarget, string> = {
  source: "来源与大纲",
  art: "美术参考",
  script: "剧本",
  "storyboard-review": "分镜评审",
};

export function sourceWorkflowTarget(value: string): SourceWorkflowTarget | undefined {
  return (sourceWorkflowTargets as readonly string[]).includes(value) ? value as SourceWorkflowTarget : undefined;
}

/** A validated source fragment keeps its source-stage owner while naming the creator's active work. */
export function sourceWorkflowLabel(value: string) {
  const target = sourceWorkflowTarget(value);
  return target ? sourceWorkflowLabels[target] : undefined;
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
