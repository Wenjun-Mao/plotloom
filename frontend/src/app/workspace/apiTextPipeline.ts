/** Only a validated, explicit runtime capability admits generic API execution. */
export function apiTextPipelineMessage(enabled: boolean | null): string {
  return enabled === false
    ? "此服务未启用 API 文本流水线。请在来源与大纲中使用生成助手，逐步审阅并确认；保留的 API 运行仅显示摘要。"
    : "服务功能尚未读入，API 文本流水线暂不可用。请等待读取完成，或使用“重新读取服务功能”重试。";
}
