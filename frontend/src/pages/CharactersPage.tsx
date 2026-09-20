import { CastPanel } from "./CastPanel";
import { CharacterReferenceReviewPanel } from "./CharacterReferenceGalleryPage";

/** One creator task: settle cast text, then establish appearance for future shots. */
export function CharactersPage({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  return <section className="page characters-page" data-testid="characters-stage">
    <header className="page-header"><div><span>角色</span><h1>角色文字与外观</h1><p>先审核角色文字，再用已有图像建立未来镜头可复用的身份参考。候选不会自动成为选择，准备 handoff 也不会自动生成。</p></div></header>
    <CastPanel projectId={projectId} readOnly={readOnly} />
    <CharacterReferenceReviewPanel projectId={projectId} readOnly={readOnly} />
  </section>;
}
