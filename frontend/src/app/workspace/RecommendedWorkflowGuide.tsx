import { Button } from "../../components";
import type { RecommendedWorkflowModel, RecommendedWorkflowRoute } from "./recommendedWorkflow";

export function RecommendedWorkflowGuide({ model, actionDisabled, onNavigate }: {
  model: RecommendedWorkflowModel | null;
  actionDisabled: boolean;
  onNavigate: (route: RecommendedWorkflowRoute) => void;
}) {
  if (!model) return null;
  const currentIndex = model.steps.findIndex(step => step.id === model.currentStep) + 1;
  const action = model.action;
  return <section className="recommended-workflow-guide" aria-label="推荐创作流程" data-testid="recommended-workflow">
    <div className="recommended-workflow-compact">
      <div className="recommended-workflow-current">
        <strong>推荐创作流程</strong>
        <span>当前 · {currentIndex}/{model.steps.length} {model.currentStepLabel}{model.currentViewLabel && ` · ${model.currentViewLabel}`}</span>
      </div>
      <details className="recommended-workflow-details">
        <summary>查看六步状态</summary>
        <div className="recommended-workflow-expanded">
          <ol aria-label="推荐流程步骤">
            {model.steps.map(step => <li key={step.id} aria-current={step.id === model.currentStep ? "step" : undefined}>
              <strong>{step.label}</strong><span>{step.status}</span>
            </li>)}
          </ol>
          <p>推荐顺序：{model.steps.map(step => step.label).join(" → ")}。序号表示当前工作步骤，不是完成比例；创作与专业视图同属剧情图编辑，切换不会退回前一步。可返回前序工作或直接手工编辑；保存、确认与应用仍由现有页面负责。</p>
          <p>播放会在路线分歧处等待选择；静态报告只供阅读，不构成交互式播放。</p>
        </div>
      </details>
    </div>
    <div className="recommended-workflow-next">
      <p><strong>下一步建议：</strong>{model.nextText}</p>
      {action?.kind === "navigate" && <Button variant="quiet" disabled={actionDisabled} onClick={() => onNavigate(action.route)}>{action.label}</Button>}
      {action?.kind === "play" && <a className="button quiet" href={action.href} target="_blank" rel="noreferrer">{action.label}</a>}
    </div>
  </section>;
}
