/** Pass only the frozen request context; source substrings never grant exemptions. */
export function providerContext(request) {
  return {providerLiteralContract: request?.inputArtifacts?.['provider-literal-contract.json'] ?? null};
}
export function castLiteralContext(candidate, request) {
  return {...providerContext(request), providerLiterals: candidate.providerLiterals ?? []};
}
