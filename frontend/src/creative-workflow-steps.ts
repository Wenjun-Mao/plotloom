export const creativeWorkflowSteps = [
  { id: "brief", label: "项目简报" },
  { id: "source", label: "来源与大纲" },
  { id: "branches", label: "剧情分支" },
  { id: "creator", label: "剧情图编辑" },
  { id: "production", label: "制作与审阅" },
  { id: "play", label: "播放" },
] as const;

export type CreativeWorkflowStepId = typeof creativeWorkflowSteps[number]["id"];

export function creativeWorkflowStepReference(id: CreativeWorkflowStepId): string {
  const index = creativeWorkflowSteps.findIndex(step => step.id === id);
  return `第${index + 1}/${creativeWorkflowSteps.length}步「${creativeWorkflowSteps[index].label}」`;
}
