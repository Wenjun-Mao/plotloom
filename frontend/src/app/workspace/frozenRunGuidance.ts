export type FrozenRunCredentialIssue = "missing-key" | "missing-profile" | "read-failed";

export function frozenRunCredentialMessage(profileId: string, issue: FrozenRunCredentialIssue, detail = ""): string {
  const guidance: Record<FrozenRunCredentialIssue, string> = {
    "missing-key": "此任务缺少可用密钥。请为任务创建时选定的模型配置补充当前标签页密钥，再重试刚才的操作。保存密钥不会自动运行任务。",
    "missing-profile": "任务创建时选定的模型配置已不存在，无法为此任务发出新的执行请求。",
    "read-failed": "暂时无法读取此任务的模型配置，未发出新的执行请求。请刷新页面后重试读取。",
  };
  return `${guidance[issue]}不会自动切换模型或模型配置。配置标识：${profileId}。${detail ? `诊断信息：${detail}` : ""}`;
}
