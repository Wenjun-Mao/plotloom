import { reviewContextMessage, type ReviewContextFailure } from "../../pages/ReviewContextNotice";

const owners = { source: "来源与大纲", characters: "角色", art: "美术参考", script: "剧本", brief: "项目简报与创作设置", "storyboard-review": "分镜评审" } as const;

/** An operation rejection is verified evidence, not an invitation to retry blindly. */
export function reviewWorkflowFailureText(error: ReviewContextFailure): string {
  if (typeof error === "string") return "本次操作未完成。先处理本页显示的错误提示，再继续；当前内容未因此获得确认。";
  if (["binding_revision_changed", "binding_content_changed", "binding_value_changed", "section_context_changed", "art_render_contract_changed", "cast_render_contract_changed"].includes(error.code)) {
    return `${reviewContextMessage(error)}先处理本页的创作依据提示，不要继续使用旧候选。`;
  }
  const control = owners[error.owner];
  return `${reviewContextMessage(error)}点击${error.owner === "brief" ? "「" : "左侧「"}${control}」，处理该页当前任务后再返回。`;
}
