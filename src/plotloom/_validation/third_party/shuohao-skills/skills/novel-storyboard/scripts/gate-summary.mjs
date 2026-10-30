// Plotloom-owned evaluated-gate presentation contract, 2026-10-09.
// Kept inside each portable skill; parity is checked by the fork selftest.
export function summarizeGates(gates) {
  const counts = { executed: 0, passed: 0, failed: 0, skipped: 0 };
  for (const gate of gates) {
    if (typeof gate.evaluated !== 'boolean' || typeof gate.ok !== 'boolean'
        || (!gate.evaluated && !gate.ok)) {
      throw new TypeError('Every gate needs explicit evaluation and admission results');
    }
    if (!gate.evaluated) counts.skipped++;
    else {
      counts.executed++;
      if (gate.ok) counts.passed++;
      else counts.failed++;
    }
  }
  return counts;
}

export function gateSummaryText(gates, lang = 'zh') {
  const { executed, passed, skipped } = summarizeGates(gates);
  const main = lang === 'en'
    ? `Executed checks ${passed} / ${executed} passed`
    : `已执行检查 ${passed} / ${executed} 通过`;
  return main + (skipped ? (lang === 'en' ? ` · ${skipped} skipped` : ` · 跳过 ${skipped} 项`) : '');
}

export function gateMarker(gate) {
  return gate.evaluated ? (gate.ok ? '✓' : '✗') : '—';
}

export function gateClass(gate) {
  return gate.evaluated ? (gate.ok ? 'ok' : 'bad') : 'skip';
}

