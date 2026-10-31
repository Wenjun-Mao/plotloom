/** Pure route validation shared by Continue and last-choice replay. */
export type Clip = { slot: string; src: string; durationUnits: number; dialogue: { speaker: string; text: string }[]; visibleText: string[] };
export type Node = { id: string; title: string; clips: Clip[]; question: string; edges: { id: string; to: string; label: string | null }[]; ending: { title: string; text: string } | null };
export type Story = { format: 1; gameId: string; storyRevision: string; assetVersion: string; title: string; intro: string; start: string; nodes: Node[] };
export type Save = { revision: string; path: string[]; clip: number; time: number; finished: boolean };

export function validateSave(story: Story, raw: unknown): Save | null {
  if (!raw || typeof raw !== "object") return null;
  const save = raw as Save;
  if (save.revision !== story.storyRevision || !Array.isArray(save.path) || save.path[0] !== story.start || save.path.length > story.nodes.length) return null;
  if (!Number.isInteger(save.clip) || save.clip < 0 || !Number.isFinite(save.time) || save.time < 0 || typeof save.finished !== "boolean") return null;
  for (let i = 0; i < save.path.length; i++) {
    const node = story.nodes.find(node => node.id === save.path[i]);
    if (!node || (i > 0 && !story.nodes.find(node => node.id === save.path[i - 1])?.edges.some(edge => edge.to === node.id))) return null;
  }
  const node = story.nodes.find(node => node.id === save.path.at(-1))!;
  if (save.clip >= Math.max(1, node.clips.length) || save.time > (node.clips[save.clip]?.durationUnits || 0) / 1000 + .1) return null;
  return { revision: save.revision, path: [...save.path], clip: save.clip, time: save.time, finished: save.finished };
}

export function lastChoicePath(story: Story, path: string[]): string[] | null {
  // Skip the current choice: "back" means the preceding decision if already there.
  const from = path.length - 2;
  for (let i = from; i >= 0; i--) {
    if (story.nodes.find(node => node.id === path[i])?.edges.some(edge => edge.label !== null)) return path.slice(0, i + 1);
  }
  return null;
}
