import { castTextPresentation } from "./cast-text-presentation";

export function castDesignErrors(character: Record<string, unknown>) {
  const persona = character.persona && typeof character.persona === "object" ? character.persona as Record<string, unknown> : {};
  const traits = persona.personality;
  const hasText = (value: unknown) => Boolean(castTextPresentation(value).text.trim());
  return {
    personality: !Array.isArray(traits) || !traits.every((value) => typeof value === "string") || !traits.some(hasText)
      ? "请至少填写一个性格特点。" : "",
    appearance: !hasText(persona.appearance) ? "请填写角色外观，作为后续外观参考的依据。" : "",
  };
}

export function hasValidCastDesign(characters: Array<Record<string, unknown>>) {
  return characters.length > 0 && characters.every((character) => !Object.values(castDesignErrors(character)).some(Boolean));
}
