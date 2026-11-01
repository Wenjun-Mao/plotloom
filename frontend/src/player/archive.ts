import type { Story } from "./state";

export type Route = { path: string[]; ending: string };
export type Archive = { revision: string; routes: Route[] };
export function readArchive(story: Story, raw: unknown): Archive {
  const empty = { revision: story.storyRevision, routes: [] };
  if (!raw || typeof raw !== "object") return empty;
  const value = raw as Archive;
  if (value.revision !== story.storyRevision || !Array.isArray(value.routes)) return empty;
  const routes = value.routes.filter(route => {
    if (!route || !Array.isArray(route.path) || route.path[0] !== story.start || route.path.length > story.nodes.length) return false;
    return route.path.every((id, i) => story.nodes.some(node => node.id === id && (!i || story.nodes.find(n => n.id === route.path[i - 1])?.edges.some(edge => edge.to === id))))
      && route.path.at(-1) === route.ending && !!story.nodes.find(node => node.id === route.ending)?.ending;
  });
  return { revision: value.revision, routes };
}
export function recordRoute(archive: Archive, path: string[]): Archive {
  if (archive.routes.some(route => JSON.stringify(route.path) === JSON.stringify(path))) return archive;
  return { ...archive, routes: [...archive.routes, { path: [...path], ending: path.at(-1)! }] };
}
export function journal(story: Story, path: string[]) {
  return path.slice(0, -1).flatMap((id, index) => {
    const node = story.nodes.find(node => node.id === id)!;
    const edge = node.edges.find(edge => edge.to === path[index + 1]);
    return edge?.label ? [{ title: node.question || node.title, label: edge.label, path: path.slice(0, index + 1) }] : [];
  });
}
