#!/usr/bin/env node
/** Saved-Brief character validation retaining the pinned upstream structural gate. */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  STYLE_PRESETS, SUPPORTED_STYLES, validateCast, needsUiTranslation, renderHtml, renderMarkdown,
} from '../third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs';

// This neutral runtime-only preset lets validateCast retain all structure,
// language and source-evidence checks without imposing a render aesthetic.
STYLE_PRESETS['saved-brief'] = {
  label: { zh: 'Saved Brief direction', en: 'Saved Brief direction', ja: 'Saved Brief direction' },
  render: '', surface: '', lighting: '', negative: '', tags: [],
};
SUPPORTED_STYLES.push('saved-brief');

function main(args) {
  const [command, castPath] = args;
  const flag = name => {
    const index = args.indexOf(name);
    if (index < 0 || !args[index + 1]) throw new Error(`Missing ${name}`);
    return args[index + 1];
  };
  if (!['validate', 'render'].includes(command) || !castPath) throw new Error('Use validate|render cast.json [--request request.json] [--md]');
  const read = path => JSON.parse(readFileSync(path, 'utf8'));
  const cast = read(castPath);
  const requestIndex = args.indexOf('--request');
  const request = requestIndex >= 0 ? read(flag('--request')) : null;
  if (request && typeof request.source?.text !== 'string') throw new Error('Frozen source.text is required for verbatim evidence validation');
  const issues = validateCast(cast.characters, request ? request.source.text : null, cast.lang, cast.style);
  if (typeof cast.summary !== 'string' || !cast.summary.trim()) issues.push('summary is required');
  if (needsUiTranslation(cast.lang) && !cast.ui) issues.push('report language requires ui translation');
  if (issues.length) throw new Error(issues.join('\n'));
  if (command === 'render') process.stdout.write(args.includes('--md')
    ? renderMarkdown(cast.characters, cast.source, cast.summary, cast.lang, cast.ui)
    : renderHtml(cast.characters, cast.source, cast.summary, cast.lang, cast.ui, cast.style));
  else process.stdout.write('Valid character structure (saved Brief style authority)\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
