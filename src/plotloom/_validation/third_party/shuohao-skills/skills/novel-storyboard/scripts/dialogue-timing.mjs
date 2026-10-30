// Modified by Plotloom, 2026-10-28. Frozen parity with canonical dialogue.bilingual.v2.
// Node 18+ stdlib; local copy keeps each skill independently usable.
export const TIMING_POLICY_VERSION = 'dialogue.bilingual.v2';
const RATES = Object.freeze({ measured: [420, 85, 500], natural: [330, 70, 400], brisk: [260, 55, 330] });
// Match Python str.strip/re whitespace exactly, including NEL and separators.
const SPACE = '[\\u0009-\\u000d\\u001c-\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]';
const trim = value => value.replace(new RegExp(`^${SPACE}+|${SPACE}+$`, 'gu'), '');
export function dialogueMilliseconds(text, locale, delivery) {
  const value = String(text ?? '');
  const [zhRate, charRate, wordRate] = Object.hasOwn(RATES, delivery) ? RATES[delivery] : RATES.natural;
  if (locale === 'zh-CN') return Array.from(trim(value)).length * zhRate;
  const chars = Array.from(value.replace(new RegExp(SPACE, 'gu'), '')).length;
  if (locale === 'en-US' || locale === 'en') return Math.max(chars * charRate, (trim(value) ? trim(value).split(new RegExp(`${SPACE}+`, 'u')).length : 0) * wordRate);
  return Array.from(trim(value)).length * charRate;
}
export function dialogueSeconds(beat, reportLang) {
  const explicit = Object.hasOwn(beat ?? {}, 'language');
  if (explicit && !['zh-CN', 'en-US'].includes(beat.language)) {
    throw new Error('Spoken cue language must be exactly zh-CN or en-US; use only a source-supported deliberate language exception');
  }
  const locale = explicit ? beat.language : (reportLang === 'en' ? 'en-US' : 'zh-CN');
  return dialogueMilliseconds(beat?.line, locale, beat?.delivery) / 1000;
}
export function timingProblems(params = {}) {
  if (params == null) params = {};
  if (typeof params !== 'object' || Array.isArray(params)) return ['params must be an object'];
  const bad = ['charsPerSecond', 'maxLineChars', 'wordsPerSecond', 'charRate', 'wordRate'].filter(k => Object.hasOwn(params, k));
  const problems = bad.map(k => `params.${k} is not supported; speech rates belong to ${TIMING_POLICY_VERSION}`);
  if (params.timingPolicyVersion != null && params.timingPolicyVersion !== TIMING_POLICY_VERSION) problems.push(`params.timingPolicyVersion must be ${TIMING_POLICY_VERSION}`);
  return problems;
}
export function requireTiming(params = {}) {
  const problems = timingProblems(params);
  if (problems.length) throw new Error(problems.join('; '));
}
