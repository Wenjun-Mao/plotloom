export type HumanReviewAttribution = { kind: "unnamed_creator" };

export function humanReviewLabel(value: { reviewer: string; attribution?: HumanReviewAttribution }) {
  if (value.attribution?.kind === "unnamed_creator") return "创作者确认（未署名）";
  return value.reviewer || "署名信息待核实";
}
