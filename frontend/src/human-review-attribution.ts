export type HumanReviewAttribution = { kind: "unnamed_creator" } | { kind: "agent_operated_qa"; scopeId: string };

export function humanReviewLabel(value: { reviewer: string; attribution?: HumanReviewAttribution }) {
  if (value.attribution?.kind === "agent_operated_qa") return "代理 QA 审阅（经用户授权）";
  if (value.attribution?.kind === "unnamed_creator") return "创作者确认（未署名）";
  return value.reviewer || "署名信息待核实";
}
