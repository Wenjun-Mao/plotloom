/** Lossless display of explicit suffix annotations; never interpret arbitrary prose. */
export function castTextPresentation(value: unknown): { text: string; annotation: string } {
  if (typeof value !== "string") return { text: "", annotation: "" };
  const match = /\s*(?:（推断）|\(推断\))\s*$/.exec(value);
  if (!match) return { text: value, annotation: "" };
  return { text: value.slice(0, match.index), annotation: match[0] };
}

export function editCastText(original: unknown, text: string): string {
  return text + castTextPresentation(original).annotation;
}
