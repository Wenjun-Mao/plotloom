/** Style-complete synthetic fixture; never used to rewrite a native candidate. */
export function styledCastFixture(cast: any, contract: any): any {
  const result = structuredClone(cast);
  const preset = contract.preset;
  result.style = contract.style;
  for (const character of result.characters) character.image = {
    ...character.image, style: preset.label, prompt: preset.render, sheet: preset.render,
    negativePrompt: preset.negative, tags: preset.tags,
  };
  return result;
}
