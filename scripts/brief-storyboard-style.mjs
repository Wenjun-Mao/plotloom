#!/usr/bin/env node
/** F5A receiving gate: inherited Brief authority plus every pinned upstream gate. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { STYLE_PRESETS, validateStoryboard, renderHtml, loadRecipes } from '../third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs';
import { validateF5ReceivingTiming } from './storyboard-dialogue-timing.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const canonical = value => JSON.stringify(sort(value));
function sort(value) {
  if (Array.isArray(value)) return value.map(sort);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sort(value[key])]));
  return value;
}
const hash = value => createHash('sha256').update(canonical(value)).digest('hex');
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const read = path => JSON.parse(readFileSync(path, 'utf8'));

// Only this entrypoint adds an authority marker, without a visual preset.
// The upstream style gate checks membership in every frame; its other gates
// and renderer use the original payload and complete frozen input context.
STYLE_PRESETS['saved-brief'] = { zh: 'Saved Brief direction', phrase: 'saved brief direction' };

export function frozenContext(request) {
  assert(request?.stage === 'storyboard', 'Frozen storyboard request is required');
  const inputs = request.inputArtifacts;
  const contract = inputs?.['storyboard-style-contract.json'];
  assert(contract?.version === 'plotloom.saved-brief.storyboard.v1' && contract.authority === 'saved_brief', 'Missing or wrong saved-Brief storyboard authority');
  assert(contract.stageInstructionContract === 'plotloom.autopilot.saved-brief-storyboard-receiving-contract.v1', 'Wrong storyboard receiving contract');
  const { contentHash, ...payload } = contract;
  assert(contentHash === hash(payload), 'Mutated storyboard style contract');
  const inherited = contract.inheritedArtRenderContract;
  assert(inherited?.authority === 'saved_brief', 'Inherited Art authority is required');
  const { contentHash: parentHash, ...parent } = inherited;
  assert(parentHash === hash(parent), 'Mutated inherited Art authority');
  assert(contract.direction === inherited.direction && contract.emptyDirectionRule === inherited.emptyDirectionRule, 'Storyboard direction must equal inherited Art direction');
  assert(contract.direction === null || typeof contract.direction === 'string', 'Inherited direction must be text or empty');
  const files = {
    policy: 'src/plotloom/storyboard_brief_style.py', adapter: 'scripts/brief-storyboard-style.mjs',
    upstream: 'third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs',
    upstreamGateSummary: 'third_party/shuohao-skills/skills/novel-storyboard/scripts/gate-summary.mjs',
    dialogueTiming: 'scripts/storyboard-dialogue-timing.mjs',
  };
  assert(canonical(Object.keys(contract.validatorHashes ?? {}).sort()) === canonical(Object.keys(files).sort()), 'Storyboard validator identities are required');
  for (const [name, path] of Object.entries(files)) {
    const actual = createHash('sha256').update(readFileSync(resolve(root, path))).digest('hex');
    assert(contract.validatorHashes[name] === actual, `Frozen storyboard ${name} identity changed`);
  }
  const admission = inputs['storyboard-admission.json'];
  assert(admission && inputs['script.json'] && inputs['outline.json'] && inputs['cast.json'], 'Frozen storyboard inputs are required');
  assert(request.source?.acceptedScriptRevision === admission.scriptRevision && request.source?.acceptedScriptContentHash === admission.scriptContentHash, 'Frozen script identity differs from admission');
  return { script: inputs['script.json'], outline: inputs['outline.json'], cast: inputs['cast.json'], art: inputs['art.json'], admission };
}

export function validateBriefStoryboard(board, request, recipes = null) {
  const ctx = frozenContext(request);
  assert(board?.style === 'saved-brief', 'storyboard.style must identify saved Brief authority');
  assert(board.promptLang === 'en', 'saved-Brief storyboard promptLang must be en');
  const admission = ctx.admission;
  const mapping = admission.sectionBindings;
  assert(Array.isArray(mapping) && canonical(board.episodes?.map(ep => ep.ep)) === canonical(mapping.map(item => item.episode)), 'Storyboard episodes must exactly match frozen F4 mapping');
  const timing = admission.reviewTiming;
  assert(timing && Object.entries(timing).every(([key, value]) => board.params?.[key] === value), 'Storyboard params must match frozen review timing');
  const durations = new Map(mapping.map((item, index) => [item.sectionId,
    board.episodes[index].segments?.reduce((total, segment) => total + (segment.cuts ?? []).reduce((sum, cut) => sum + cut.seconds, 0), 0)]));
  const footage = new Set(admission.completeRouteSectionIds.flat().filter(id => !admission.routeOnlySectionIds.includes(id)));
  assert(footage.size === durations.size && [...durations].every(([id, seconds]) => footage.has(id) && Number.isFinite(seconds) && seconds > 0), 'Storyboard timing must cover every footage section exactly');
  assert(admission.completeRouteSectionIds.every(route => route.reduce((sum, id) => sum + (durations.get(id) ?? 0), 0) <= admission.targetPlaythroughSeconds + 0.0001), 'Complete storyboard route exceeds author playthrough maximum');
  const issues = validateStoryboard(board, { ...ctx, recipes });
  assert(!issues.length, issues.join('\n'));
  validateF5ReceivingTiming(board, request);
  return { ...ctx, recipes };
}

function main(args) {
  const [command, path] = args;
  const flag = name => { const index = args.indexOf(name); assert(index >= 0 && args[index + 1], `Missing ${name}`); return args[index + 1]; };
  assert(['validate', 'render'].includes(command) && path, 'Use validate|render storyboard.json --request request.json [--shots card-directory]');
  const board = read(path), request = read(flag('--request'));
  const shots = args.includes('--shots') ? flag('--shots') : null;
  if (shots) assert(!/\.json$/i.test(shots), '--shots requires source card directory');
  const recipes = shots ? loadRecipes(shots) : null;
  if (shots) assert(recipes.size > 0, '--shots contains no recipe cards');
  const ctx = validateBriefStoryboard(board, request, recipes);
  process.stdout.write(command === 'render' ? renderHtml(board, ctx) : 'Valid storyboard (saved Brief authority; semantic fidelity requires human review)\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
