#!/usr/bin/env node
/** Preset/manual F5 admission retains every upstream gate plus canonical timing. */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateStoryboard, renderHtml, loadRecipes } from '../third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs';
import { validateF5ReceivingTiming } from './storyboard-dialogue-timing.mjs';

export function validateReceivedStoryboard(board, request, recipes = null) {
  const inputs = request?.inputArtifacts;
  if (!inputs?.['script.json'] || !inputs['outline.json'] || !inputs['cast.json']) throw new Error('Frozen storyboard source inputs are required');
  const ctx = { script: inputs['script.json'], outline: inputs['outline.json'], cast: inputs['cast.json'], art: inputs['art.json'], recipes };
  const issues = validateStoryboard(board, ctx);
  if (issues.length) throw new Error(issues.join('\n'));
  validateF5ReceivingTiming(board, request);
  return ctx;
}

function main(args) {
  const [command, path] = args, index = args.indexOf('--request');
  if (!['validate', 'render'].includes(command) || !path || index < 0 || !args[index + 1]) throw new Error('Use validate|render storyboard.json --request request.json [--shots card-directory]');
  const read = path => JSON.parse(readFileSync(path, 'utf8'));
  const shotsIndex = args.indexOf('--shots');
  const recipes = shotsIndex < 0 ? null : loadRecipes(args[shotsIndex + 1]);
  const board = read(path), ctx = validateReceivedStoryboard(board, read(args[index + 1]), recipes);
  process.stdout.write(command === 'render' ? renderHtml(board, ctx) : 'Valid storyboard (upstream and canonical receiving timing)\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
