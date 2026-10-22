#!/usr/bin/env node
/** Current Plotloom character render contract; candidate bytes are never translated. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import {
  STYLE_PRESETS, SUPPORTED_STYLES, validateCast, needsUiTranslation,
  renderHtml, renderMarkdown,
} from '../third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs';

STYLE_PRESETS['live-action'] = {
  label: { zh: '真人写实', en: 'Live-action photography', ja: '実写写真' },
  render: 'Live-action photographic character reference, natural human anatomy and photographic texture, physically plausible materials and cinematic realism',
  surface: 'Natural skin texture and asymmetry, individual hair strands, believable fabric weave, weight and wear; no painted surfaces or plastic doll finish',
  lighting: 'Soft directional portrait lighting in the left zone; even neutral reference lighting for the right-side full-body views and detail strip, preserving consistent identity and readable proportions',
  negative: 'illustration, anime, painterly rendering, brush strokes, plastic CG look, waxy skin, malformed hands, extra fingers, text, watermark, signature',
  tags: ['live-action', 'photographic', 'character reference', 'natural texture'],
};
SUPPORTED_STYLES.push('live-action');

export function styleContract(style, authorDirection) {
  if (!SUPPORTED_STYLES.includes(style)) throw new Error('Choose a supported character render style explicitly.');
  return {
    version: 1, style, authorDirection,
    preset: { ...STYLE_PRESETS[style], label: STYLE_PRESETS[style].label.zh },
    implementationHash: createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  };
}

export function validateStyle(cast, contract) {
  if (!contract) return ['character render contract is missing; prepare a new task'];
  const expected = styleContract(contract.style, contract.authorDirection);
  const errors = [];
  if (!isDeepStrictEqual(contract, expected)) errors.push('character render contract is stale; prepare a new task');
  if (cast.style !== contract.style) errors.push('cast.style must equal the frozen character render style');
  for (const character of cast.characters ?? []) {
    const img = character.image ?? {};
    if (img.style !== expected.preset.label) errors.push(`${character.id}: image.style must match the frozen style label`);
    for (const field of ['prompt', 'sheet']) {
      if (typeof img[field] !== 'string' || !img[field].includes(expected.preset.render)) errors.push(`${character.id}: image.${field} must include the frozen render direction`);
    }
    const positive = [img.prompt, img.sheet, ...(Array.isArray(img.tags) ? img.tags : [])].join(' ');
    const incompatible = {
      'live-action': /painterly|brush\s*(stroke|texture|work)|semi[- ]realistic|\banime\b|\billustration\b|\bconcept art\b/i,
      realistic: /live[- ]action|photographic reference|\banime\b|\bghibli\b/i,
      ghibli: /live[- ]action|photographic reference|photorealistic|3d render|semi[- ]realistic/i,
    }[contract.style];
    if (incompatible.test(positive)) errors.push(`${character.id}: positive image direction conflicts with ${contract.style}`);
    if (typeof img.negativePrompt !== 'string' || !img.negativePrompt.trim()) errors.push(`${character.id}: image.negativePrompt is required`);
    if (['live-action', 'realistic'].includes(contract.style) && /photorealis|photograph|live[- ]action|3d render/i.test(img.negativePrompt ?? '')) errors.push(`${character.id}: negative prompt must not ban the selected realism`);
    if (contract.style === 'ghibli' && !/photorealistic|3d render/i.test(img.negativePrompt ?? '')) errors.push(`${character.id}: animation negative prompt must exclude photorealism`);
  }
  return errors;
}

function main(args) {
  const [command, path] = args;
  const flag = name => { const i = args.indexOf(name); if (i < 0 || !args[i + 1]) throw new Error(`Missing ${name}`); return args[i + 1]; };
  const read = path => JSON.parse(readFileSync(path, 'utf8'));
  if (command === 'contract') {
    process.stdout.write(JSON.stringify(styleContract(flag('--style'), JSON.parse(flag('--author-direction')))));
    return;
  }
  if (!['check-style', 'validate', 'render'].includes(command) || !path) throw new Error('Use validate|render cast.json --request request.json --contract cast-style-contract.json [--md]');
  const cast = read(path), contract = read(flag('--contract'));
  const problems = validateStyle(cast, contract);
  if (command !== 'check-style') {
    const source = read(flag('--request')).source;
    if (typeof source.text !== 'string') throw new Error('Frozen source.text is required for verbatim evidence validation');
    problems.push(...validateCast(cast.characters, source.text, cast.lang, cast.style));
    if (typeof cast.summary !== 'string' || !cast.summary.trim()) problems.push('summary is required');
    if (needsUiTranslation(cast.lang) && !cast.ui) problems.push('report language requires ui translation');
  }
  if (problems.length) throw new Error(problems.join('\n'));
  if (command === 'render') process.stdout.write(args.includes('--md')
    ? renderMarkdown(cast.characters, cast.source, cast.summary, cast.lang, cast.ui)
    : renderHtml(cast.characters, cast.source, cast.summary, cast.lang, cast.ui, cast.style));
  else process.stdout.write(`Valid character ${command} (${contract.preset.label})\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
