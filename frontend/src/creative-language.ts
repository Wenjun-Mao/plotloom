/** Creative defaults only. Application copy is owned by the Chinese UI.
 * Existing authored values are never passed through this helper.
 */
export const supportsCreativeLanguage = (language: string) => language === "en-US" || language === "zh-CN";

export function creativeDefaults(language: string) {
  if (language === "en-US") return {
    title: "Untitled story", entity: "Unnamed entity", scene: "New scene",
    shot: "New shot", narrator: "Narrator", cameraAngle: "Eye level",
    cameraMovement: "Static", transition: "Cut",
  };
  if (language === "zh-CN") return {
    title: "未命名故事", entity: "未命名实体", scene: "新场景",
    shot: "新镜头", narrator: "旁白", cameraAngle: "平视",
    cameraMovement: "固定", transition: "硬切",
  };
  throw new Error("此项目语言暂不支持新增创作内容。请在项目简报中选择简体中文或英语后再试。");
}

export function canonicalBriefTitle(title: string, language: string): string {
  return title.trim() || (supportsCreativeLanguage(language) ? creativeDefaults(language).title : "");
}
