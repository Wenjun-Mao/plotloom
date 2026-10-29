import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { expect, it } from "vitest";

// Exceptions are exact, feature-owned technical text or brand identities.
// See UI_COPY_EXCEPTIONS.md. Authored expressions and report HTML are not UI copy.
const exceptions: Record<string, string[]> = {
  "app/workspace/WorkspaceController.tsx": ["Plotloom"],
  "features/media/image-jobs/ImageJobPanel.tsx": ["PLOTLOOM_IMAGE_EXCHANGE_ROOT"],
  "features/specialists/SpecialistSettingsDialog.tsx": ["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
  "pages/ArtPanel.tsx": ["· sha256:"],
  "pages/StoryPrototypePage.tsx": ["Plotloom"],
  "play/PlayView.tsx": ["Plotloom"],
  "structured-fields.tsx": ["JSON"],
  "video-end-frame.tsx": ["SHA-256"],
};
function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory()
    ? sourceFiles(path.join(directory, entry.name))
    : entry.name.endsWith(".tsx") ? [path.join(directory, entry.name)] : []);
}
const normalCopyAttributes = new Set(["label", "title", "placeholder", "description", "aria-label"]);

it("keeps static Chinese application chrome free of untranslated normal copy", () => {
  const root = path.resolve(import.meta.dirname, "../src"), findings: string[] = [], used = new Set<string>();
  for (const file of sourceFiles(root)) {
    const relative = path.relative(root, file).split(path.sep).join("/"), source = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const check = (value: string, node: ts.Node) => {
      const text = value.replace(/\s+/g, " ").trim();
      if (!/[A-Za-z]{3}/.test(text) || /[\u3400-\u9fff]/.test(text)) return;
      if (exceptions[relative]?.includes(text)) { used.add(`${relative}:${text}`); return; }
      findings.push(`${relative}:${source.getLineAndCharacterOfPosition(node.getStart()).line + 1}: ${text}`);
    };
    const visit = (node: ts.Node) => {
      if (ts.isJsxText(node)) check(node.text, node);
      if (ts.isJsxAttribute(node) && normalCopyAttributes.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) check(node.initializer.text, node);
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  expect(findings).toEqual([]);
  expect([...used].sort()).toEqual(Object.entries(exceptions).flatMap(([file, values]) => values.map(value => `${file}:${value}`)).sort());
});
