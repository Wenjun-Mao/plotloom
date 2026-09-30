import type { ArtReferenceProposal } from "../types";

export type ArtReferenceSubject = {
  subjectType: "scene" | "prop";
  subjectId: string;
  name: string;
  content: Record<string, unknown>;
};

export function artSubjects(art: Record<string, unknown>): ArtReferenceSubject[] {
  return (["scene", "prop"] as const).flatMap((subjectType) => {
    const items = art[subjectType === "scene" ? "scenes" : "props"];
    return Array.isArray(items) ? items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && typeof item.id === "string").map((item) => ({ subjectType, subjectId: item.id as string, name: String(item.name || item.id), content: item })) : [];
  });
}

export function subjectKey(subject: ArtReferenceSubject) { return `${subject.subjectType}:${subject.subjectId}`; }

export function artStyleLabel(style: unknown) {
  switch (style) {
    case "live-action": return "真人写实";
    case "realistic": return "半写实厚涂";
    case "ghibli": return "吉卜力动画";
    default: return "已接受的美术风格";
  }
}

export function defaultImageRequirements(style: unknown, subjectType: "scene" | "prop") {
  const subject = subjectType === "scene"
    ? "保持已确认的环境布局、关键物件与光线，不添加人物。"
    : "保持已确认的道具造型、材质与细节，白色背景，不添加人物或手。";
  return `沿用${artStyleLabel(style)}，遵循已接受的美术设定。${subject}`;
}

export function studyStatus(study: ArtReferenceProposal | undefined) {
  if (!study) return "未准备";
  if (study.state === "cancelled") return "已取消";
  if (!study.current) return "设定已变更";
  if (study.deliveries.some((delivery) => delivery.state === "rejected")) return "交付未通过检查";
  if (study.state === "delivered") return "图片已返回";
  return study.state === "prepared" ? "待发送" : "等待图片";
}

export function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
