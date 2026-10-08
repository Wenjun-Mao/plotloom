import { ApiError } from "../../api";
import { messageFrom, type ProjectLoadFailure } from "./contracts";

export function projectLoadFailure(error: unknown, projectId: string, authoritativeMissing = false): ProjectLoadFailure {
  const code = error instanceof ApiError ? (error.details as { code?: unknown } | undefined)?.code : undefined;
  return {
    projectId,
    kind: error instanceof ApiError && error.status === 409 && code === "project_closed"
      ? "closed" : authoritativeMissing ? "missing" : "unavailable",
    diagnostic: messageFrom(error),
  };
}

export const projectUnavailableCopy = {
  closed: { title: "项目已关闭", description: "故事内容和媒体仍保留。请打开项目目录，明确重新打开这个项目后再继续。" },
  missing: { title: "找不到这个项目", description: "服务器确认当前项目目录中没有这个项目。请核对链接，或在项目目录中选择已有项目。" },
  unavailable: { title: "暂时无法读取项目", description: "本次未能核实项目内容。请重新读取，或打开项目目录查看；这不代表项目已被删除。" },
  "continuation-failed": { title: "后台运行未能继续", description: "项目已读入，当前内容仍保留。请查看运行轨迹并重新核实状态；不要重复发送新的生成任务。" },
} satisfies Record<ProjectLoadFailure["kind"], { title: string; description: string }>;

export function projectLoadFailureMessage(failure: ProjectLoadFailure): string {
  const copy = projectUnavailableCopy[failure.kind];
  return `${copy.title}：${copy.description}${failure.kind === "continuation-failed" ? "" : "本次读取未完成；没有回退到示例或空白草稿。"}`;
}
