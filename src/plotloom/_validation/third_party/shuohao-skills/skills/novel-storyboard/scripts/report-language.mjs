// Modified by Plotloom, 2026-10-28: explicit immutable report locale.
// Kept within each independently copyable skill; Node 18+, stdlib only.
export const REPORT_LANGUAGES = Object.freeze(['zh', 'en']);
export function languageProblems(doc, expected) {
  const problems = [];
  if (doc?.ui != null) problems.push('Custom ui overrides are not supported for frozen bilingual reports');
  if (expected != null && !REPORT_LANGUAGES.includes(expected)) problems.push('Report language must be zh / en');
  if (!REPORT_LANGUAGES.includes(doc?.lang)) problems.push('lang must explicitly be zh / en (报告语言必须明确为 zh 或 en)');
  if (expected != null && expected !== doc?.lang) problems.push('Report locale conflicts with candidate.lang; regenerate from the frozen language contract (报告语言不一致)');
  return problems;
}
export function reportLanguage(doc, expected) {
  const problems = languageProblems(doc, expected);
  if (problems.length) throw new Error(problems.join('; '));
  return doc.lang;
}
export function readableGateDetail(g, label, translated) {
  if (translated != null) return translated;
  if (!g.detail) return '';
  if (g.ok) return `Check satisfied [${g.id}]: ${label}.`;
  return `Failed check [${g.id}]: ${label}. Correct the affected source entries.`;
}
export function artScaleLabel(value, lang) {
  const names = { '手持级': 'Handheld scale', '桌面级': 'Tabletop scale', '家具级': 'Furniture scale' };
  return lang === 'en' ? (names[value] ?? value) : value;
}
export function adaptationModeLabel(value, lang) {
  return lang === 'en' ? ({ '忠实': 'Faithful', '抽核': 'Core adaptation', '借壳': 'Reimagined' }[value] ?? value) : value;
}

/** Exact raw diagnostics remain inspectable technical evidence, outside primary prose. */
export function gateTechnicalHtml(gate, lang, escape) {
  if (lang !== 'en' || !gate.detail) return '';
  return `<details class="gate-diagnostic"><summary>Technical source diagnostic [${escape(gate.id)}]</summary><pre>${escape(gate.detail)}</pre></details>`;
}
export function gateMarkdown(gates, lang, textFor, heading) {
  const out = [`## ${heading ?? (lang === 'en' ? 'Quality checks' : '质量门')}`, ''];
  for (const g of gates) {
    const text = textFor(g, lang);
    out.push(`- ${g.evaluated ? (g.ok ? '✅' : '❌') : '—'} ${text.label}${(!g.evaluated || !g.ok) && g.detail ? ` — ${text.detail}` : ''}`);
  }
  const diagnostics = lang === 'en' ? gates.filter(g => g.detail) : [];
  if (diagnostics.length) {
    out.push('', '### Technical source diagnostics', '');
    for (const g of diagnostics) {
      const raw = String(g.detail);
      // Longer than any source backtick run, so source text cannot close its fence.
      const fence = '`'.repeat(Math.max(3, ...[...raw.matchAll(/`+/g)].map(m => m[0].length + 1)));
      out.push(`**[${g.id}]**`, '', fence + 'text', raw, fence, '');
    }
  }
  return out.join('\n');
}
