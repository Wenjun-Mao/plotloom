#!/usr/bin/env node
/** Brief-style path retaining the pinned upstream Art structural gate. */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SCENE_STYLE_PRESETS, SUPPORTED_STYLES, validateArt, renderHtml } from '../third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs';

// Saved Brief authority is a workflow mode, not an upstream visual preset.
// Add a neutral runtime-only preset so the pinned validator still enforces its
// full structural and quality gates without injecting a default art direction.
SCENE_STYLE_PRESETS['saved-brief'] = {
  label: 'Saved Brief direction', render: '', surface: '', lighting: '', negative: '', tags: [],
};
SUPPORTED_STYLES.push('saved-brief');

function main(args) {
  const [command, artPath] = args;
  const flag = name => { const index = args.indexOf(name); if (index < 0 || !args[index + 1]) throw new Error(`Missing ${name}`); return args[index + 1]; };
  if (!['validate', 'render'].includes(command) || !artPath) throw new Error('Use validate|render art.json --cast cast.json');
  const read = path => JSON.parse(readFileSync(path, 'utf8'));
  const art = read(artPath), cast = read(flag('--cast'));
  const context = { cast };
  const issues = validateArt(art, context);
  if (issues.length) throw new Error(issues.join('\n'));
  if (command === 'render') process.stdout.write(renderHtml(art, context));
  else process.stdout.write('Valid art structure (saved Brief style authority)\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
