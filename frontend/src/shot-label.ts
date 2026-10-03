import type { Shot } from "./types";

/** Display-only labels never change frozen source or production authority. */
export function shotLabel(shot: Partial<Pick<Shot, "id" | "title" | "action">>, fallback = "当前镜头"): string {
  const title = shot.title?.trim();
  const value = title && Array.from(title).length <= 64
    ? title : shot.action?.trim() || shot.id || fallback;
  const characters = Array.from(value);
  return characters.length > 52 ? `${characters.slice(0, 51).join("")}…` : value;
}
