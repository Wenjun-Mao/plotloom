/** Interpret the JSON number's decimal value, as the production bridge does. */
export function sourceSecondsToMilliseconds(seconds: unknown): number | undefined {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0) return undefined;
  const [decimal, exponent = "0"] = seconds.toString().split("e");
  const fractionDigits = decimal.split(".")[1]?.length ?? 0;
  const coefficient = BigInt(decimal.replace(".", ""));
  const scale = Number(exponent) + 3 - fractionDigits;
  const divisor = scale < 0 ? 10n ** BigInt(-scale) : 1n;
  const numerator = scale > 0 ? coefficient * 10n ** BigInt(scale) : coefficient;
  if (numerator % divisor !== 0n) return undefined;
  const milliseconds = numerator / divisor;
  // Canonical duration units must remain exact in the browser's number domain.
  if (milliseconds > BigInt(Number.MAX_SAFE_INTEGER)) return undefined;
  return Number(milliseconds);
}
