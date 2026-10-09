#!/usr/bin/env node
/** Plotloom's explicit art preset extension; pinned fork structure/gates stay intact. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import {
  SCENE_STYLE_PRESETS, SUPPORTED_STYLES, validateArt,
  renderHtml, renderMarkdown,
} from '../third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs';

SCENE_STYLE_PRESETS['live-action'] = {
  label: '真人写实',
  render: 'Live-action photographic reference, physically plausible materials and lighting, natural photographic texture, cinematic realism',
  surface: 'Believable material detail and wear appropriate to the setting, natural reflections, restrained colour and photographic surface detail',
  negative: 'people, human figures, characters, crowds, painterly rendering, brush strokes, illustration, anime, plastic CG look, warped perspective, text, watermark, signature',
  tags: ['live-action', 'photographic', 'cinematic realism'],
};
SUPPORTED_STYLES.push('live-action');

export function styleContract(style, authorDirection) {
  if (!SUPPORTED_STYLES.includes(style)) throw new Error('Choose a supported art render style explicitly.');
  return {
    version: 1, style, authorDirection,
    preset: SCENE_STYLE_PRESETS[style],
    adapterHash: createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  };
}

export function validateStyledArt(art, cast, contract) {
  const problems = validateArt(art, { cast });
  const expected = styleContract(contract.style, contract.authorDirection);
  if (contract.version !== expected.version || contract.adapterHash !== expected.adapterHash
      || !isDeepStrictEqual(contract.preset, expected.preset)) problems.push('art style contract is stale; prepare a new task');
  if (art.style !== contract.style) problems.push('art.style must equal the frozen author-selected style');
  for (const subject of [...(art.scenes ?? []), ...(art.props ?? [])]) {
      const img = subject.image ?? {};
      for (const field of ['prompt', 'sheet']) {
        if (!String(img[field] ?? '').includes(expected.preset.render)) problems.push(`${subject.id}: image.${field} must include the selected render direction`);
      }
      const positive = [img.prompt, img.sheet, ...(img.tags ?? []),
        ...(subject.lighting ?? []).map(item => item.prompt),
        ...(subject.states ?? []).map(item => item.prompt)].join(' ');
      const incompatible = {
        'live-action': /painterly|brush\s*(stroke|texture|work)|semi[- ]realistic|\banime\b|\billustration\b|\bconcept art\b/i,
        realistic: /live[- ]action|photographic reference|\banime\b|\bghibli\b/i,
        ghibli: /live[- ]action|photographic reference|photorealistic|3d render|semi[- ]realistic/i,
      }[contract.style];
      if (incompatible.test(positive)) problems.push(`${subject.id}: positive image directions conflict with ${contract.style}`);
      if (contract.style === 'live-action' && /photorealis|photograph|live[- ]action/i.test(img.negativePrompt ?? '')) problems.push(`${subject.id}: negative prompt must not ban live-action photography`);
  }
  return problems;
}

function main(args) {
  const [command, path] = args;
  const flag = name => { const i = args.indexOf(name); if (i < 0 || !args[i + 1]) throw new Error(`Missing ${name}`); return args[i + 1]; };
  const read = path => JSON.parse(readFileSync(path, 'utf8'));
  if (command === 'contract') {
    process.stdout.write(JSON.stringify(styleContract(flag('--style'), JSON.parse(flag('--author-direction')))));
    return;
  }
  if (!['validate', 'render'].includes(command) || !path) throw new Error('Use validate|render art.json --cast cast.json --contract art-style-contract.json [--html|--md]');
  const art = read(path), cast = read(flag('--cast')), contract = read(flag('--contract'));
  const problems = validateStyledArt(art, cast, contract);
  if (problems.length) throw new Error(problems.join('\n'));
  if (command === 'validate') process.stdout.write(`Valid art (${contract.preset.label})\n`);
  else process.stdout.write(args.includes('--md') ? renderMarkdown(art, { cast, lang: 'zh' }) : renderHtml(art, { cast, lang: 'zh' }));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
