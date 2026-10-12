import type { SourceMaterial } from "../../types";

/** An author edit cannot retain the trusted code's exact-Brief assertion. */
export function authoredSource(value: SourceMaterial): SourceMaterial {
  const { briefOrigin: _origin, ...authored } = value;
  return authored;
}
